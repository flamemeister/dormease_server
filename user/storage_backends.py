from storages.backends.s3boto3 import S3Boto3Storage

class MinioProfileImageStorage(S3Boto3Storage):
    bucket_name = 'dormitory-files'
    location = 'profile-images'  
    default_acl = 'public-read'
