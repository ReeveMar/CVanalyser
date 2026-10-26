# AWS S3 & IAM Configuration Guide for CV Analyser

This guide provides step-by-step instructions for creating and hardening an **AWS S3 Bucket** and setting up a **Least-Privilege IAM User** for the CV Analyser application. Both AWS Management Console and AWS CLI instructions are included.

---

## Prerequisites
- An active AWS Account.
- AWS CLI installed and configured locally (`aws configure`), OR access to the AWS Web Console.

---

## Part 1: S3 Bucket Setup & Hardening

### Step 1: Create the S3 Bucket

Bucket names in AWS must be globally unique across all AWS accounts.
Example bucket name: `cvanalyser-storage-production`

#### Option A: Using AWS CLI
```bash
# Set your preferred region (e.g., us-east-1, eu-west-2, ap-southeast-1)
export AWS_REGION="us-east-1"
export BUCKET_NAME="cvanalyser-storage-production"

# If us-east-1:
aws s3api create-bucket \
  --bucket $BUCKET_NAME \
  --region $AWS_REGION

# If any other region (e.g., eu-west-2):
# aws s3api create-bucket \
#   --bucket $BUCKET_NAME \
#   --region $AWS_REGION \
#   --create-bucket-configuration LocationConstraint=$AWS_REGION
```

#### Option B: Using AWS Management Console
1. Navigate to **Amazon S3** > **Buckets** > **Create bucket**.
2. **Bucket name**: Enter your unique name (e.g. `cvanalyser-storage-production`).
3. **AWS Region**: Select the region closest to your server (e.g. `US East (N. Virginia) us-east-1`).
4. Keep the remaining settings default for now and click **Create bucket**.

---

### Step 2: Enforce "Block All Public Access" (CRITICAL FOR CV PRIVACY)

CVs contain personal identifiable information (PII). The bucket must NEVER be publicly readable. All file access is routed securely through authenticated backend API streams or pre-signed URLs.

#### AWS CLI:
```bash
aws s3api put-public-access-block \
  --bucket $BUCKET_NAME \
  --public-access-block-configuration "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"
```

#### AWS Console:
1. Open your bucket > Click the **Permissions** tab.
2. Under **Block public access (bucket settings)**, click **Edit**.
3. Ensure **Block *all* public access** is **CHECKED**.
4. Click **Save changes** and type `confirm`.

---

### Step 3: Enable Server-Side Encryption (SSE-S3)

Encrypts all CV files at rest using AES-256.

#### AWS CLI:
```bash
aws s3api put-bucket-encryption \
  --bucket $BUCKET_NAME \
  --server-side-encryption-configuration '{
    "Rules": [
      {
        "ApplyServerSideEncryptionByDefault": {
          "SSEAlgorithm": "AES256"
        },
        "BucketKeyEnabled": true
      }
    ]
  }'
```

#### AWS Console:
1. In your bucket, select the **Properties** tab.
2. Scroll to **Default encryption** > click **Edit**.
3. **Encryption type**: Select **Server-side encryption with Amazon S3 managed keys (SSE-S3)**.
4. **Bucket Key**: Enable.
5. Click **Save changes**.

---

### Step 4: Enable Bucket Versioning (Recommended)

Protects against accidental deletion and maintains an audit trail of CV edits.

#### AWS CLI:
```bash
aws s3api put-bucket-versioning \
  --bucket $BUCKET_NAME \
  --versioning-configuration Status=Enabled
```

#### AWS Console:
1. In the **Properties** tab > **Bucket Versioning** > click **Edit**.
2. Select **Enable** > click **Save changes**.

---

### Step 5: Configure S3 Lifecycle Rules (Storage Cost Optimization)

Automatically permanently delete old generated cover letters and temporary artifacts after 7 days, while keeping original uploaded CVs.

#### AWS CLI:
Create a JSON file named `lifecycle.json`:
```json
{
  "Rules": [
    {
      "ID": "ExpireGeneratedArtifacts",
      "Filter": {
        "Prefix": "user-files/*/generated/"
      },
      "Status": "Enabled",
      "Expiration": {
        "Days": 7
      },
      "NoncurrentVersionExpiration": {
        "NoncurrentDays": 3
      }
    }
  ]
}
```
Apply rule:
```bash
aws s3api put-bucket-lifecycle-configuration \
  --bucket $BUCKET_NAME \
  --lifecycle-configuration file://lifecycle.json
```

---

## Part 2: IAM Least-Privilege Setup

Never use your root AWS credentials or an admin user in your application. Create a dedicated service user with permissions restricted solely to this bucket.

---

### Step 1: Create the IAM Policy

1. Navigate to **IAM** > **Policies** > **Create policy**.
2. Click the **JSON** tab and paste the following policy (replace `cvanalyser-storage-production` with your actual bucket name):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowListBucket",
      "Effect": "Allow",
      "Action": [
        "s3:ListBucket",
        "s3:GetBucketLocation"
      ],
      "Resource": "arn:aws:s3:::cvanalyser-storage-production"
    },
    {
      "Sid": "AllowCVFileOperations",
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:DeleteObject"
      ],
      "Resource": "arn:aws:s3:::cvanalyser-storage-production/*"
    }
  ]
}
```

3. Click **Next**.
4. Policy Name: `CVAnalyserS3AccessPolicy`.
5. Click **Create policy**.

#### Using AWS CLI:
```bash
aws iam create-policy \
  --policy-name CVAnalyserS3AccessPolicy \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Sid": "AllowListBucket",
        "Effect": "Allow",
        "Action": ["s3:ListBucket", "s3:GetBucketLocation"],
        "Resource": "arn:aws:s3:::cvanalyser-storage-production"
      },
      {
        "Sid": "AllowCVFileOperations",
        "Effect": "Allow",
        "Action": ["s3:PutObject", "s3:GetObject", "s3:DeleteObject"],
        "Resource": "arn:aws:s3:::cvanalyser-storage-production/*"
      }
    ]
  }'
```

---

### Step 2: Create IAM User & Attach Policy

1. Navigate to **IAM** > **Users** > **Create user**.
2. **User name**: `cvanalyser-app-user`.
3. Do **NOT** enable AWS Management Console access (this user is only for API access).
4. Click **Next**.
5. Select **Attach policies directly**.
6. Search for `CVAnalyserS3AccessPolicy` and check its box.
7. Click **Next** > **Create user**.

---

### Step 3: Generate Access Keys

1. Click on the newly created user `cvanalyser-app-user`.
2. Go to the **Security credentials** tab.
3. Under **Access keys**, click **Create access key**.
4. Select **Application running outside AWS** > click **Next**.
5. Description tag: `CV Analyser Ubuntu Server`.
6. Click **Create access key**.
7. **IMPORTANT**: Copy the **Access key ID** and **Secret access key**. (The secret key will only be shown once).

---

## Part 3: Adding Credentials to Your Production Server

On your Ubuntu server, paste the credentials into `.env.prod`:

```ini
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_REGION=us-east-1
S3_BUCKET_NAME=cvanalyser-storage-production
```

### Verification Test
You can quickly verify that your credentials work using Python:
```bash
python3 -c "
import boto3
s3 = boto3.client('s3', aws_access_key_id='AKIA...', aws_secret_access_key='...', region_name='us-east-1')
print(s3.list_objects_v2(Bucket='cvanalyser-storage-production'))
"
```
If this prints a valid response without AccessDenied, your AWS configuration is 100% complete!
