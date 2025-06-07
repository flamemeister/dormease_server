import boto3

s3 = boto3.client(
    's3',
    endpoint_url='http://localhost:9000',
    aws_access_key_id='minioadmin',
    aws_secret_access_key='minioadmin123'
)

# Путь к локальному файлу
file_path = 'requirements.txt'

# Название бакета и путь внутри него
bucket_name = 'dormitory-files'
object_name = 'test/requirements.txt'  # или 'requirements.txt'

s3.upload_file(file_path, bucket_name, object_name)

print(f" Uploaded to http://localhost:9000/{bucket_name}/{object_name}")
