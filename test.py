
from boto3 import client
from pydantic import BaseModel

class CustomS3Config(BaseModel):
    aws_access_key_id : str = "minio_access_key"
    aws_secret_access_key : str = "minio_secret_key"
    endpoint_url: str = "http://localhost:9000"
    #bucket: str = "default"
    use_ssl: bool = False
config=CustomS3Config()
session = client("s3",**config.dict())
from s3fs import S3FileSystem
s3 = S3FileSystem(client_kwargs=config.dict())
s3.ls("test")
