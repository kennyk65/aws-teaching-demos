import base64

def generate_base64_encoded_image():
    red_pixel_png_base64 = (
        b'iVBORw0KGgoAAAANSUhEUgAAABQAAAAUCAYAAACNiR0NAAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAAJcEhZcwAAHYcAAB2HAY/l8WUAAAAlSURBVDhPYxDN3P2fmnjUQMrxqIGU41EDKcejBlKOR5yBu/8DAGE+d65GwLbaAAAAAElFTkSuQmCC'
    )
    return red_pixel_png_base64

def lambda_handler(event, context):
    # Your logic to generate or retrieve the base64-encoded image string
    base64_encoded_image = generate_base64_encoded_image()

    # Decode base64 to binary
    binary_image_data = base64.b64decode(base64_encoded_image)

    # Calculate content length
    content_length = str(len(binary_image_data))
    
    
    # Formulate the API Gateway response
    response = {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'image/png',  # Set the appropriate image MIME type
            'Content-Length': content_length,            
            'Content-Disposition': 'inline',
            'Accept-Ranges': 'bytes'
        },
        'body': base64_encoded_image,
        'isBase64Encoded': True,
    }

    return response
