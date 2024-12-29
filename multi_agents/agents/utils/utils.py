import re

def sanitize_filename(filename: str) -> str:
    """
    Sanitize a given filename by replacing characters that are invalid 
    in Windows file paths with an underscore ('_').

    This function ensures that the filename is compatible with all 
    operating systems by removing or replacing characters that are 
    not allowed in Windows file paths. Specifically, it replaces 
    the following characters: < > : " / \\ | ? * and spaces

    Parameters:
    filename (str): The original filename to be sanitized.

    Returns:
    str: The sanitized filename with invalid characters replaced by an underscore.
    
    Examples:
    >>> sanitize_filename('invalid:file/name*example?.txt')
    'invalid_file_name_example_.txt'
    
    >>> sanitize_filename('valid filename.txt')
    'valid_filename.txt'
    """
    # First, replace spaces with underscores
    filename = filename.replace(' ', '_')
    
    # Then replace other invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Replace multiple underscores with a single underscore
    filename = re.sub(r'_+', '_', filename)
    
    # Remove any leading or trailing underscores
    filename = filename.strip('_')
    
    return filename
