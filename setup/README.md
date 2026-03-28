# Project Setup (Windows)

## Initial Requirements For Computer
- python3
- pip
- Docker Desktop
- ffmpeg

## Terminology:
### Some one time setup is required, while for every session after, a smaller amount of activation is required. To keep these clear, please note the following terms. 
### Setup: One time setup required, Activate: An activation step required every session

## Setup Instructions
### Step 1: Environment Variable
#### Setup:
Within the project folder, please create a .env variable with the following fields. These instructions will detail filling each one by one
```{bash}
GROQ_API_KEY=
HUGGINGFACE_TOKEN=
SUPABASE_URL=
SUPABASE_KEY=
LIVEKIT_API_KEY=
LIVEKIT_API_SECRET=
```

### Step 2: Docker Image
#### Setup:
```{bash}
cd src/docker
docker build -t n8n_image:latest .
docker compose --env-file ../../.env up -d
```
#### Activate:
```{bash}
cd src/docker
docker compose --env-file ../../.env up -d
```
#### Check: 
You can confirm this has been setup correctly by running this test link to n8n (save for later) http://localhost:5678

### Step 3: Groq Token
#### Setup:
Create an account or sign in to https://console.groq.com/home. Press "API Keys". Press "Create API Key", copy its value upon completion then set in .env as GROQ_API_KEY.

### Step 4: Huggingface Token
#### Setup:
Create an account or sign in to https://huggingface.co/. Press the Profile Icon on the top right, then press "Access Tokens". Press "Create new token", select type "Read" and copy its value upon completion to set in .env as HUGGINGFACE_TOKEN

### Step 5: Supabase
#### Setup: 
If you dont have a supabase account, you can create one for free at https://supabase.com/. Once signed in press "Dashboard". Select your default org. Press "Create A Project" and upon completion, press "SQL Editor". Paste the SQL query within src/supabase/ then press run. Press "Table Editor" and you should see a new table created called "segment". Confirm it exists. Then press "Project Settings". In the centre of the screen you should see a "Project ID". Within your .env set SUPABASE_URL=https://{id}.supabase.co. Next press "API Keys". Under "Secret Keys" copy the default, or create your own, then paste it into your .env variable as SUPABASE_KEY.

### Step 6: Virtual Environment + FastAPI
#### Setup:
```{bash}
cd src/python_venv
python3 -m venv script_env
.\script_env\Scripts\Activate.ps1
pip install -r python_env_dependancies.txt
cd ..
uvicorn python_venv.endpoints:app --host 0.0.0.0 --port 8000 --reload
```
#### Activate:
```{bash}
cd src/python_venv
.\script_env\Scripts\Activate.ps1
cd ..
uvicorn python_venv.endpoints:app --host 0.0.0.0 --port 8000 --reload
```
#### Note: 
You may recieve a warning about huggingface token authentication, it is a byproduct of the free token type in use, you can safely ignore it. 
#### Check: 
You can confirm this has been setup correctly by running this test endpoint http://localhost:8000/test-status

### Step 7: N8N
#### Setup: 
Assuming the above docker step has been completed and activated, please access N8N using http://localhost:5678. Create account or sign in, and upon completion, press "Create Workflow", press "...". From here, press "Import From File", then select the contents of src/n8n. This will load the main N8N flow. From here press the Supabase node, press "Setup Credential", then supply the 2 supabase fields within .env. Confirm N8N validates the connection, then close the menu then press "Publish"  

### Step 8: Front 
#### Activation: The frontend can be simply activated with the command line
#### LiveKit cannot run from opening the index.html file. 
#### We are required to run a local server for the frontend.
```{bash}
cd src/frontend
python -m http.server 3000
http://localhost:3000
```