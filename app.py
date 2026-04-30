from flask import Flask, render_template, request, redirect, url_for, flash
import boto3
import os
from datetime import datetime
import uuid

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# AWS Configuration
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')
S3_BUCKET = os.environ.get('S3_BUCKET_NAME', 'your-bucket-name')

def get_s3_client():
    return boto3.client(
        's3',
        region_name=AWS_REGION,
        aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY')
    )

# ─── Page 1: Home ───────────────────────────────────────────────────────────

@app.route('/')
def home():
    # Fetch uploaded files from S3 to display on home page
    files = []
    try:
        s3 = get_s3_client()
        response = s3.list_objects_v2(Bucket=S3_BUCKET)
        if 'Contents' in response:
            for obj in response['Contents']:
                files.append({
                    'name': obj['Key'],
                    'size': round(obj['Size'] / 1024, 2),
                    'last_modified': obj['LastModified'].strftime('%Y-%m-%d %H:%M')
                })
    except Exception as e:
        flash(f'Could not connect to S3: {str(e)}', 'error')

    return render_template('home.html', files=files, now=datetime.now())


# ─── Page 2: Upload ──────────────────────────────────────────────────────────

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file selected.', 'error')
            return redirect(request.url)

        file = request.files['file']
        if file.filename == '':
            flash('No file selected.', 'error')
            return redirect(request.url)

        if file:
            # Generate unique filename
            ext = file.filename.rsplit('.', 1)[-1] if '.' in file.filename else 'bin'
            unique_name = f"{uuid.uuid4().hex[:8]}_{file.filename}"

            try:
                s3 = get_s3_client()
                s3.upload_fileobj(
                    file,
                    S3_BUCKET,
                    unique_name,
                    ExtraArgs={'ContentType': file.content_type or 'application/octet-stream'}
                )
                flash(f'✅ File "{file.filename}" uploaded successfully to S3!', 'success')
            except Exception as e:
                flash(f'Upload failed: {str(e)}', 'error')

            return redirect(url_for('upload'))

    return render_template('upload.html', now=datetime.now())


# ─── Health Check (for load balancer) ───────────────────────────────────────

@app.route('/health')
def health():
    return {'status': 'healthy', 'timestamp': datetime.now().isoformat()}, 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
