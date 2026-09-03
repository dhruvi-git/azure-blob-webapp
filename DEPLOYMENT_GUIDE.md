# Deploying the File Manager to Azure (App Service + Blob Storage)

Architecture:
`User → Web App (Azure App Service, PaaS) → Azure Blob Storage → Files/Blobs`

This guide uses the **Azure CLI**, which works the same on Windows/Mac/Linux and is the
fastest way to reproduce every step. A Portal-only walkthrough is noted at the bottom
of each section if you prefer clicking through the Azure Portal instead.

---

## 0. Prerequisites

- An Azure account (free student/trial account is fine): https://azure.microsoft.com/free/
- [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli) installed
- Python 3.10+ installed locally (for testing before deploy)
- This project folder (`azure-blob-webapp/`)

Login first:
```bash
az login
```

---

## 1. Create a Resource Group

A resource group is just a logical container for all resources in this lab.

```bash
az group create --name rg-blob-webapp --location centralindia
```

---

## 2. Create the Storage Account and Blob Container

Storage account names must be **globally unique, lowercase, 3–24 chars, no hyphens**.
Replace `stblobwebapp123` with something unique to you.

```bash
az storage account create \
  --name stblobwebapp123 \
  --resource-group rg-blob-webapp \
  --location centralindia \
  --sku Standard_LRS \
  --kind StorageV2

# Get the connection string (copy this — you'll need it in step 4)
az storage account show-connection-string \
  --name stblobwebapp123 \
  --resource-group rg-blob-webapp \
  --query connectionString -o tsv

# Create the container (the app also auto-creates it on first run, so this is optional)
az storage container create \
  --name uploads \
  --connection-string "<paste-connection-string-here>"
```

**Portal alternative:** Storage accounts → Create → fill Resource group/Name/Region →
Review + create. Then Containers → + Container → name it `uploads`.
Get the connection string from **Access keys** in the left menu.

---

## 3. Test the app locally (optional but recommended)

```bash
cd azure-blob-webapp
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

export AZURE_STORAGE_CONNECTION_STRING="<paste-connection-string-here>"   # Windows: set VAR=...
export AZURE_STORAGE_CONTAINER_NAME="uploads"

python app.py
# Visit http://localhost:8000
```
Upload a test photo and a document, confirm they appear in the list.

---

## 4. Create the App Service (the PaaS layer) and deploy the code

### Option A — `az webapp up` (simplest, creates the App Service Plan + Web App together)

```bash
cd azure-blob-webapp
az webapp up \
  --name blob-webapp-<yourname>123 \
  --resource-group rg-blob-webapp \
  --location centralindia \
  --sku F1 \
  --runtime "PYTHON:3.11"
```
(App names are globally unique too — the URL will be `https://blob-webapp-<yourname>123.azurewebsites.net`)

### Option B — explicit step-by-step (more control)

```bash
# App Service plan (Linux, free tier F1)
az appservice plan create \
  --name plan-blob-webapp \
  --resource-group rg-blob-webapp \
  --sku F1 \
  --is-linux

# Web App
az webapp create \
  --name blob-webapp-<yourname>123 \
  --resource-group rg-blob-webapp \
  --plan plan-blob-webapp \
  --runtime "PYTHON:3.11"

# Zip and deploy the code
zip -r app.zip . -x "venv/*" ".git/*"
az webapp deploy \
  --resource-group rg-blob-webapp \
  --name blob-webapp-<yourname>123 \
  --src-path app.zip \
  --type zip
```

---

## 5. Configure app settings (environment variables)

The app reads the storage connection string from environment variables — set these
on the Web App so it can talk to Blob Storage:

```bash
az webapp config appsettings set \
  --name blob-webapp-<yourname>123 \
  --resource-group rg-blob-webapp \
  --settings \
    AZURE_STORAGE_CONNECTION_STRING="<paste-connection-string-here>" \
    AZURE_STORAGE_CONTAINER_NAME="uploads" \
    SECRET_KEY="some-random-secret-string" \
    SCM_DO_BUILD_DURING_DEPLOYMENT="true"
```

Set the startup command so App Service runs gunicorn correctly:

```bash
az webapp config set \
  --name blob-webapp-<yourname>123 \
  --resource-group rg-blob-webapp \
  --startup-file "gunicorn --bind=0.0.0.0 --timeout 600 app:app"
```

Restart to apply:
```bash
az webapp restart --name blob-webapp-<yourname>123 --resource-group rg-blob-webapp
```

**Portal alternative:** Web App → Configuration → Application settings → + New application
setting (add the three above) → Save. Then General settings → Startup Command → paste
the gunicorn command → Save.

---

## 6. Verify the deployment

Open:
```
https://blob-webapp-<yourname>123.azurewebsites.net
```

- Confirm the file list loads (empty at first).
- Upload a personal photograph (e.g. `photo.jpg`).
- Upload a document (e.g. `resume.pdf`).
- Refresh — both files should now appear in the listing with size and timestamp.
- Click a file name to confirm it opens directly from Blob Storage.

If you see an error about `AZURE_STORAGE_CONNECTION_STRING`, double-check step 5 and
restart the app.

---

## 7. Live log tail (handy for debugging)

```bash
az webapp log tail --name blob-webapp-<yourname>123 --resource-group rg-blob-webapp
```

---

## 8. Clean up (after your submission/demo, to avoid charges)

```bash
az group delete --name rg-blob-webapp --yes --no-wait
```

---

## What to include in your submission

1. The public App Service URL: `https://blob-webapp-<yourname>123.azurewebsites.net`
2. Screenshot of the empty file listing (before upload)
3. Screenshot of the upload form with a photo/document selected
4. Screenshot of the file listing after upload, showing both files
5. Screenshot of the Azure Portal showing the Storage Account container with the same
   two blobs (proves storage-level persistence, not just app-level state)
6. This repo/zip of source code
