from storages.backends.s3boto3 import S3Boto3Storage

class MinioDocumentStorage(S3Boto3Storage):
    bucket_name = 'dormitory-files'
    location = 'applications/documents'
    default_acl = 'public-read'
    file_overwrite = False


class MinioRoomImageStorage(S3Boto3Storage):
    bucket_name = 'dormitory-files'
    location = 'rooms/images'
    default_acl = 'public-read'
    file_overwrite = False


class MinioBuildingImageStorage(S3Boto3Storage):
    bucket_name = 'dormitory-files'
    location = 'buildings/images'
    default_acl = 'public-read'
    file_overwrite = False

