# Private S3 bucket for restaurant and menu-item photos uploaded by the
# restaurants_service Lambda (see app/integrations/s3.py). Objects are stored
# under restaurants/{id}/... and menu-items/{id}/... key prefixes.
#
# Hand-written resources mirroring the SPA (frontend) bucket idiom so we keep
# fine-grained control over versioning, public-access blocking, CORS, and SSE.
#
# NOTE ON URL TENSION (follow-up, NOT addressed here): s3.py returns a
# NON-presigned, public-style URL ("https://{bucket}.s3.{region}.amazonaws.com/{key}")
# from upload_restaurant_photo / upload_menu_item_photo. That URL can only be
# rendered by a browser if the object is publicly readable. This bucket is kept
# PRIVATE per the security requirement, so those URLs will return 403 until the
# app is changed to serve objects via presigned GET URLs or a CloudFront/OAC
# distribution. Do not add public-read to "fix" this.

resource "aws_s3_bucket" "images" {
  bucket        = local.images_bucket_name
  force_destroy = true
}

resource "aws_s3_bucket_versioning" "images" {
  bucket = aws_s3_bucket.images.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_ownership_controls" "images" {
  bucket = aws_s3_bucket.images.id

  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

# PRIVATE: block all public access. This bucket must never be made public.
resource "aws_s3_bucket_public_access_block" "images" {
  bucket = aws_s3_bucket.images.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "images" {
  bucket = aws_s3_bucket.images.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# CORS for browser interaction with the photo objects. GET/HEAD cover image
# display (incl. future presigned GET); PUT/POST cover any browser-direct upload
# flow. allowed_origins is "*" because the frontend origin is not knowable from
# this backend repo. NOTE: tighten allowed_origins to the real SPA origin(s)
# (e.g. the CloudFront/frontend bucket domain) once known.
resource "aws_s3_bucket_cors_configuration" "images" {
  bucket = aws_s3_bucket.images.id

  cors_rule {
    allowed_methods = ["GET", "HEAD", "PUT", "POST"]
    allowed_headers = ["*"]
    allowed_origins = ["*"]
    expose_headers  = ["ETag"]
    max_age_seconds = 3000
  }
}
