import re
from email.parser import Parser
from email.message import EmailMessage
from io import StringIO


def parse_email_headers(email_text: str) -> dict:
    """Parse email headers and extract key information."""
    try:
        # Try to parse as RFC 822 email format
        parser = Parser()
        message = parser.parsestr(email_text)

        headers = {
            'from': message.get('From', '').strip(),
            'to': message.get('To', '').strip(),
            'subject': message.get('Subject', '').strip(),
            'date': message.get('Date', '').strip(),
            'cc': message.get('Cc', '').strip(),
            'bcc': message.get('Bcc', '').strip(),
            'reply_to': message.get('Reply-To', '').strip(),
            'content_type': message.get('Content-Type', '').strip(),
            'x_mailer': message.get('X-Mailer', '').strip(),
        }

        # Get body
        body = ''
        if message.is_multipart():
            for part in message.walk():
                if part.get_content_type() == 'text/plain':
                    body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                    break
        else:
            body = message.get_payload(decode=True).decode('utf-8', errors='ignore')

        return {
            'headers': {k: v for k, v in headers.items() if v},
            'body': body[:500],  # First 500 chars of body
            'full_text': email_text,
            'is_html': 'text/html' in headers.get('content_type', '').lower(),
        }

    except Exception as e:
        # Fallback: try regex parsing for simple cases
        return parse_email_headers_regex(email_text)


def parse_email_headers_regex(email_text: str) -> dict:
    """Fallback: Parse email headers using regex."""
    headers = {}

    # Extract headers using regex
    from_match = re.search(r'From:\s*(.+?)(?:\n|$)', email_text, re.IGNORECASE)
    to_match = re.search(r'To:\s*(.+?)(?:\n|$)', email_text, re.IGNORECASE)
    subject_match = re.search(r'Subject:\s*(.+?)(?:\n|$)', email_text, re.IGNORECASE)
    date_match = re.search(r'Date:\s*(.+?)(?:\n|$)', email_text, re.IGNORECASE)
    cc_match = re.search(r'Cc:\s*(.+?)(?:\n|$)', email_text, re.IGNORECASE)

    if from_match:
        headers['from'] = from_match.group(1).strip()
    if to_match:
        headers['to'] = to_match.group(1).strip()
    if subject_match:
        headers['subject'] = subject_match.group(1).strip()
    if date_match:
        headers['date'] = date_match.group(1).strip()
    if cc_match:
        headers['cc'] = cc_match.group(1).strip()

    # Try to split header and body
    header_end = email_text.find('\n\n')
    if header_end > 0:
        body = email_text[header_end:].strip()
    else:
        body = email_text

    return {
        'headers': headers,
        'body': body[:500],
        'full_text': email_text,
        'is_html': '<html' in email_text.lower(),
    }


def validate_email_address(email: str) -> bool:
    """Simple email validation."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def extract_email_addresses(text: str) -> list[str]:
    """Extract all email addresses from text."""
    pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    return re.findall(pattern, text)
