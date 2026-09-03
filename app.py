import os
from flask import Flask, render_template, request, redirect, url_for, flash
from azure.storage.blob import BlobServiceClient, ContentSettings

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# ---- Azure Storage configuration (set these as App Service environment variables) ----
AZURE_STORAGE_CONNECTION_STRING = os.environ.get('AZURE_STORAGE_CONNECTION_STRING')
AZURE_STORAGE_CONTAINER_NAME = os.environ.get('AZURE_STORAGE_CONTAINER_NAME', 'uploads')


def get_container_client():
    """Return a client for the target container, creating it if it doesn't exist."""
    if not AZURE_STORAGE_CONNECTION_STRING:
        raise ValueError(
            "AZURE_STORAGE_CONNECTION_STRING environment variable is not set. "
            "Configure it in Azure App Service > Configuration > Application settings."
        )
    blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
    container_client = blob_service_client.get_container_client(AZURE_STORAGE_CONTAINER_NAME)
    if not container_client.exists():
        container_client.create_container()
    return container_client


@app.route('/')
def index():
    """List all blobs currently in the container."""
    blobs = []
    try:
        container_client = get_container_client()
        for blob in container_client.list_blobs():
            blob_client = container_client.get_blob_client(blob.name)
            blobs.append({
                'name': blob.name,
                'size_kb': round((blob.size or 0) / 1024, 2),
                'last_modified': blob.last_modified.strftime('%Y-%m-%d %H:%M:%S') if blob.last_modified else 'N/A',
                'url': blob_client.url,
                'content_type': blob.content_settings.content_type if blob.content_settings else 'unknown',
            })
        blobs.sort(key=lambda b: b['last_modified'], reverse=True)
    except Exception as e:
        flash(f'Error connecting to Azure Storage: {e}', 'error')

    return render_template('index.html', blobs=blobs, container_name=AZURE_STORAGE_CONTAINER_NAME)


@app.route('/upload', methods=['POST'])
def upload_file():
    """Upload a new file (blob) to the container."""
    file = request.files.get('file')
    if not file or file.filename == '':
        flash('Please choose a file before clicking upload.', 'error')
        return redirect(url_for('index'))

    try:
        container_client = get_container_client()
        blob_client = container_client.get_blob_client(file.filename)
        content_type = file.content_type or 'application/octet-stream'
        blob_client.upload_blob(
            file.stream.read(),
            overwrite=True,
            content_settings=ContentSettings(content_type=content_type),
        )
        flash(f'"{file.filename}" uploaded successfully.', 'success')
    except Exception as e:
        flash(f'Upload failed: {e}', 'error')

    return redirect(url_for('index'))


@app.route('/delete/<path:blob_name>', methods=['POST'])
def delete_file(blob_name):
    """Optional: delete a blob from the container."""
    try:
        container_client = get_container_client()
        container_client.delete_blob(blob_name)
        flash(f'"{blob_name}" deleted.', 'success')
    except Exception as e:
        flash(f'Delete failed: {e}', 'error')
    return redirect(url_for('index'))


@app.route('/health')
def health():
    """Simple health check endpoint (useful for App Service)."""
    return {'status': 'ok'}, 200


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port, debug=True)
