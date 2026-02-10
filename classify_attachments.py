import os
import json
import re
import base64
from email import message_from_bytes
from email.message import Message
from pathlib import Path
from typing import Dict, List, Tuple
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def extract_html_body_and_attachments(eml_path: str) -> Tuple[str, List[str]]:
    # Read the file as bytes and parse it
    with open(eml_path, 'rb') as f:
        eml_bytes = f.read()
    
    # Use message_from_bytes for binary data
    msg = message_from_bytes(eml_bytes)
    
    html_body = ""
    attachments = []
    
    # Use msg.walk() which already handles recursion through all parts
    # No need to manually recurse - walk() does it for us
    for part in msg.walk():
        content_type = part.get_content_type()
        content_disposition = part.get("Content-Disposition", "")
        
        # Extract HTML body
        if content_type == "text/html" and not html_body:
            payload = part.get_payload(decode=True)
            if payload:
                try:
                    html_body = payload.decode('utf-8', errors='ignore')
                except:
                    try:
                        html_body = base64.b64decode(payload).decode('utf-8', errors='ignore')
                    except:
                        html_body = payload.decode('utf-8', errors='ignore')
        
        # Extract attachment filenames (skip the HTML body part itself)
        if content_type != "text/html":
            # Check if this is an attachment
            if content_disposition or (content_type.startswith('application/') or 
                                      content_type.startswith('image/') or 
                                      content_type.startswith('video/') or
                                      content_type.startswith('audio/')):
                filename = None
                
                # Try to get filename from Content-Disposition
                if content_disposition:
                    filename_match = re.search(r'filename[^;=\n]*=(([\'"]).*?\2|[^\s;]+)', 
                                              content_disposition, re.IGNORECASE)
                    if filename_match:
                        filename = filename_match.group(1).strip('\'"')
                
                # Try to get filename from Content-Type
                if not filename:
                    content_type_header = part.get("Content-Type", "")
                    filename_match = re.search(r'name[^;=\n]*=(([\'"]).*?\2|[^\s;]+)', 
                                              content_type_header, re.IGNORECASE)
                    if filename_match:
                        filename = filename_match.group(1).strip('\'"')
                
                # Include if it matches the expected pattern (example_XXXXX_attachment_YY.ext)
                if filename and re.match(r'example_\d+_attachment_\d+\.', filename):
                    attachments.append(filename)
    
    return html_body, sorted(set(attachments))


def clean_html_for_analysis(html: str) -> str:
    if not html:
        return ""
    
    # Decode HTML entities if needed
    import html as html_lib
    try:
        html = html_lib.unescape(html)
    except:
        pass
    
    # Remove excessive whitespace but preserve structure
    html = re.sub(r'\s+', ' ', html)
    html = re.sub(r'>\s+<', '><', html)
    
    return html.strip()


# Prompt template for classifying attachments
CLASSIFICATION_PROMPT_TEMPLATE = """You are analyzing an email to classify its attachments. 

The email's HTML body is provided below. Based ONLY on the HTML content, classify each attachment as either "relevant" or "irrelevant".

- **relevant**: Attachments that contain meaningful information that should be extracted from the email. This includes:
  - Documents (PDFs, Word docs, spreadsheets, etc.)
  - Reports, invoices, receipts, forms, orders, contracts
  - Data files (CSV, JSON, etc.)
  - Document-scan images (scanned documents, receipts, forms, letters, etc. - even if they are images, they contain document content)
  - Images that are mentioned alongside documents or as part of a document set
  - Any attachment that contains substantive information or data from the email
  - If the email mentions "attached X documents/files/orders/etc", count the attachments and ensure the mentioned number are classified as relevant
  
- **irrelevant**: Attachments that are just noise in the HTML. This includes:
  - Social media icons (Facebook, Twitter, LinkedIn logos, etc.)
  - Company logos used for branding (unless they are part of a document)
  - Signature images (decorative signature graphics embedded in email signatures)
  - Decorative images (banners, dividers, background images)
  - Marketing images (newsletter headers, promotional graphics)
  - Any image that is purely decorative or branding-related and NOT mentioned as a document

CRITICAL RULES:
- Base your classification ONLY on how the attachment is referenced or used in the HTML body
- Do NOT use the filename, file type, Content-Disposition, or any other metadata
- IGNORE generic legal disclaimers that mention "attachments" - these are boilerplate text and don't refer to specific attachments
- Focus on the ACTUAL EMAIL CONTENT (the main message body, not email headers, signatures, or disclaimers)

RELEVANT attachments are those that:
1. Are explicitly mentioned in the email content (e.g., "see attached 5 orders", "please find attached documents", "attached files")
2. Are part of a COUNTED set: If email says "5 attached orders" or "attached 5 documents", you MUST classify EXACTLY that many non-decorative attachments as relevant. This includes:
   - PDFs and document files
   - Image files (PNG, JPG) that are document scans (scanned orders, receipts, forms)
   - Any attachment that could contain the mentioned documents
3. Are document-scan images when email context suggests documents are being shared:
   - If email says "Orders are released", "Documents attached", or similar context suggesting documents, image attachments that could be document scans should be RELEVANT
   - When email mentions documents/orders/files in context, image attachments are likely document scans and should be RELEVANT (unless clearly decorative like logos)

IRRELEVANT attachments are those that:
1. Are NOT mentioned in the actual email content (only in generic disclaimers)
2. Are decorative images (logos, icons, signature graphics, banners) embedded in email formatting - these are clearly branding/formatting, not documents
3. Exist in emails with very short content (like "o.k.", "thanks", "Danke!") that don't mention attachments - in these cases, ALL attachments should be IRRELEVANT, even PDFs
4. Are in email threads where the current message doesn't reference them and the message is just a brief response

CRITICAL COUNTING RULE:
- If email mentions a specific number (e.g., "5 attached orders", "see attached 5 documents"), you MUST count ALL non-decorative attachments and classify that many as relevant
- When counting, include both PDFs AND image files that could be document scans
- Only exclude clearly decorative images (logos, icons) from the count
- Example: Email says "5 attached orders", there are 6 attachments (5 PDFs + 1 PNG that's a document scan + 1 JPG that's a logo) → 5 PDFs + 1 PNG = 6 relevant, 1 JPG logo = irrelevant

STRICT RULE FOR SHORT EMAILS:
- If email content is very brief (just "o.k.", "thanks", "Danke!", etc.) with NO mention of attachments, documents, or files, then ALL attachments should be IRRELEVANT, regardless of file type (even PDFs)
- Short acknowledgment emails without attachment mentions mean attachments are likely from forwarded threads and not relevant to the current message

Attachments to classify:
{attachments_json}

HTML Body:
{html_body}

Respond with a JSON object in this exact format:
{{
  "relevant": ["filename1", "filename2", ...],
  "irrelevant": ["filename3", "filename4", ...]
}}

Every attachment must be classified into exactly one category. Return only the JSON, no other text."""


def call_llm_api(prompt: str, api_key: str, model: str = None, 
                 max_tokens: int = 4096, timeout: int = 120) -> str:
    """
    Call OpenRouter API to get LLM response.
    
    Args:
        prompt: The prompt to send to the LLM
        api_key: OpenRouter API key
        model: Model identifier (default: from OPENROUTER_MODEL env var or "anthropic/claude-3.5-sonnet")
        max_tokens: Maximum tokens in response (default: 4096)
        timeout: Request timeout in seconds (default: 120)
        
    Returns:
        The response text from the LLM
        
    Raises:
        requests.exceptions.RequestException: If API call fails
    """
    # Get model from environment variable or use default
    if model is None:
        model = os.getenv("OPENROUTER_MODEL", "anthropic/claude-3.5-sonnet")
    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com",  # Optional: for tracking
        },
        json={
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": max_tokens
        },
        timeout=timeout
    )
    
    response.raise_for_status()  # Raise an exception for bad status codes
    result = response.json()
    
    return result['choices'][0]['message']['content'].strip()


def parse_llm_response(response_text: str, attachment_filenames: List[str]) -> Dict[str, List[str]]:
    """
    Parse LLM response and validate classification results.
    
    Args:
        response_text: Raw response text from LLM
        attachment_filenames: List of all attachment filenames that should be classified
        
    Returns:
        Dictionary with 'relevant' and 'irrelevant' keys containing classified filenames
    """
    # Extract JSON from response (in case there's extra text)
    json_match = re.search(r'\{[\s\S]*\}', response_text)
    if json_match:
        response_text = json_match.group(0)
    
    result = json.loads(response_text)
    
    # Get lists from response
    relevant = result.get("relevant", [])
    irrelevant = result.get("irrelevant", [])
    
    # Check for duplicates within each list
    relevant_set = set(relevant)
    irrelevant_set = set(irrelevant)
    
    if len(relevant) != len(relevant_set):
        duplicates = [item for item in relevant_set if relevant.count(item) > 1]
        print(f"  Warning: Found duplicates in 'relevant' list: {duplicates}")
        relevant = list(relevant_set)  # Remove duplicates
    
    if len(irrelevant) != len(irrelevant_set):
        duplicates = [item for item in irrelevant_set if irrelevant.count(item) > 1]
        print(f"  Warning: Found duplicates in 'irrelevant' list: {duplicates}")
        irrelevant = list(irrelevant_set)  # Remove duplicates
    
    # Check for attachments that appear in both lists
    overlap = relevant_set & irrelevant_set
    if overlap:
        print(f"  Warning: Found attachments in both 'relevant' and 'irrelevant': {overlap}")
        # Remove from irrelevant if it appears in both (prefer relevant)
        irrelevant_set = irrelevant_set - overlap
        irrelevant = list(irrelevant_set)
    
    # Remove any attachments that weren't in the original list
    all_attachments = set(attachment_filenames)
    relevant = [a for a in relevant if a in all_attachments]
    irrelevant = [a for a in irrelevant if a in all_attachments]
    
    # Validate that all attachments are classified
    all_classified = set(relevant + irrelevant)
    missing = all_attachments - all_classified
    
    # If some attachments are missing, add them to irrelevant as default
    if missing:
        print(f"  Warning: Missing classifications for: {missing}. Adding to irrelevant.")
        irrelevant.extend(list(missing))
    
    return {
        "relevant": sorted(relevant),
        "irrelevant": sorted(irrelevant)
    }


def classify_attachments(html_body: str, attachment_filenames: List[str], 
                        api_key: str) -> Dict[str, List[str]]:
    """
    Classify email attachments as relevant or irrelevant using LLM.
    
    Args:
        html_body: The HTML body of the email
        attachment_filenames: List of attachment filenames to classify
        api_key: OpenRouter API key
        
    Returns:
        Dictionary with 'relevant' and 'irrelevant' keys
    """
    if not attachment_filenames:
        return {"relevant": [], "irrelevant": []}
    
    # Clean HTML for better analysis
    cleaned_html = clean_html_for_analysis(html_body)
    
    # Truncate HTML if too long (Claude has token limits)
    max_html_length = 200000  # Leave room for prompt and response
    if len(cleaned_html) > max_html_length:
        cleaned_html = cleaned_html[:max_html_length] + "... [truncated]"
    
    # Build prompt from template
    prompt = CLASSIFICATION_PROMPT_TEMPLATE.format(
        attachments_json=json.dumps(attachment_filenames, indent=2),
        html_body=cleaned_html
    )
    
    try:
        # Call LLM API
        response_text = call_llm_api(prompt, api_key)
        
        # Parse and validate response
        return parse_llm_response(response_text, attachment_filenames)
        
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON response: {e}")
        print(f"Response was: {response_text[:500] if 'response_text' in locals() else 'N/A'}")
        # Fallback: classify all as irrelevant
        return {"relevant": [], "irrelevant": sorted(attachment_filenames)}
    except requests.exceptions.RequestException as e:
        print(f"Error calling OpenRouter API: {e}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_detail = e.response.json()
                print(f"API Error details: {error_detail}")
            except:
                print(f"API Error response: {e.response.text[:500]}")
        # Fallback: classify all as irrelevant
        return {"relevant": [], "irrelevant": sorted(attachment_filenames)}
    except Exception as e:
        print(f"Unexpected error: {e}")
        # Fallback: classify all as irrelevant
        return {"relevant": [], "irrelevant": sorted(attachment_filenames)}


def main():
    # Get API key from environment variable
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY environment variable must be set")
    
    # Setup paths
    examples_dir = Path("examples")
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    # Process all .eml files
    eml_files = sorted(examples_dir.glob("*.eml"))
    
    if not eml_files:
        print(f"No .eml files found in {examples_dir}")
        return
    
    print(f"Found {len(eml_files)} .eml files to process")
    
    for eml_file in eml_files:
        print(f"\nProcessing {eml_file.name}...")
        
        try:
            # Extract HTML body and attachments
            html_body, attachments = extract_html_body_and_attachments(str(eml_file))
            
            if not html_body:
                print(f"  Warning: No HTML body found in {eml_file.name}")
            
            if not attachments:
                print(f"  Warning: No attachments found in {eml_file.name}")
                # Create empty output
                result = {"relevant": [], "irrelevant": []}
            else:
                print(f"  Found {len(attachments)} attachments: {', '.join(attachments)}")
                
                # Classify attachments
                result = classify_attachments(html_body, attachments, api_key)
            
            # Generate output filename
            match = re.search(r'example_(\d+)', eml_file.name)
            if match:
                example_num = match.group(1)
                output_file = output_dir / f"attachments_{example_num}.json"
                
                # Write output
                with open(output_file, 'w') as f:
                    json.dump(result, f, indent=2)
                
                print(f"  ✓ Saved to {output_file}")
                print(f"    Relevant: {len(result['relevant'])}, Irrelevant: {len(result['irrelevant'])}")
            else:
                print(f"  Error: Could not extract example number from {eml_file.name}")
                
        except Exception as e:
            print(f"  Error processing {eml_file.name}: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n✓ Processing complete!")


if __name__ == "__main__":
    main()
