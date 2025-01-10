from flask import Flask, render_template, url_for, session, redirect, request
from google_auth_oauthlib.flow import Flow
from pip._vendor import cachecontrol
import google.auth.transport.requests
from google.oauth2 import id_token
from googleapiclient.discovery import build
import os
import pathlib
import requests
import json
import time
import uuid
from urllib.parse import urlencode

app = Flask(__name__)
app.secret_key = "your-secret-key@12344321"  

# Google OAuth2 credentials
CLIENT_SECRETS_FILE = "client_secret.json"
GOOGLE_CLIENT_ID = "9792465820-qnvrp2qh51v9ssbeehgmn819h3s88641.apps.googleusercontent.com"

flow = Flow.from_client_secrets_file(
    client_secrets_file=CLIENT_SECRETS_FILE,
    scopes=[
        "https://www.googleapis.com/auth/userinfo.profile", 
        "https://www.googleapis.com/auth/userinfo.email", 
        "openid",
        "https://www.googleapis.com/auth/drive"
    ],
    redirect_uri="http://127.0.0.1:5000/callback"
)

@app.route("/")
def index():
    return render_template('index.html', GOOGLE_CLIENT_ID=GOOGLE_CLIENT_ID)

@app.route("/login")
def login():
    try:
        # Get state from flow
        _, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true'
        )
        session["state"] = state

        # Generate random 'part' string similar to your working URL
        part_string = 'AJi8hAPneGlJHk46ImhIvWvo6wpF6oyU_wqOteQwZ2xteVOh0oZY6Y4wCY-G51N2b1pCXCwjZCsczjiBOL72DLOjtUOLHmhGC9ohSsZMTLQIvUkneJQHBZYWSg7Aliz_wqa0JZy7AtM29h7fk1ep2SLmIzrkoDCXdOBMeH7FcXEfZz53Dq4K9YnJyXDjUyFSsIaPNqMQAg6iMZWdWAza0iIGHOuwRW-LOInLLa0Q5JwKEQXLhb-kBFfGE_EW6B8xrMWqb4ix8iGmtBYdwZLHdr1BfQHxmGHJzG2ctS6G5O9rpRrfxHyWnBhRQ0GvtZvQ7UaEw5NeFmj9AVQn3hZslwuRKIqrscH9aixRiyrTvChYfVPo46IT6U_w3ay-RAUlrbR10xBGlapZkhSDMCV-J9WOb0R3R5wyd_0TVmPXF5pgt5DJHlVv41512xUQiyiTVPt8aTMV6jGB8icpYNSKXXf84hWte92knLZki_skQQ95QBwtT8dtodmOiRKwJ7U_9xvt6-ONGg8G_xsS8kO8RkM-TSR9x_746Kx5dqyzWcCO8mHM0vG2vbP1vYtC9CQsJdMkDN6kdOsnAvIAHKEcbDAChVszAcw_Az8LvzSwonnEzhxllJFXpaePfM1CExOtCtmIe5jJNHRSuPXzSOE8h2Gfa29rQ4d0z9oj05EZoduMSSxUZ6GST8fGK3_BalsrBubxelXcAMGW4CRKTBuWBpKVg-PJoUtnsYHtjI9xt88X9seE_8Xh8YP8ytyDb3ZqUo7IvX_8Sk5RhNc-CYpGePko67B5uc6pXg'

        # Build params matching your working URL
        params = {
            'authuser': '0',
            'client_id': GOOGLE_CLIENT_ID,
            'flowName': 'GeneralOAuthFlow',
            'state': state,
            'part': part_string,
            'as': f'S-{int(time.time()*1000)}'
        }

        if 'rapt' in session:
            params['rapt'] = session['rapt']

        # Create URL with exact endpoint
        auth_url = f'https://accounts.google.com/signin/oauth/id?{urlencode(params)}'
        
        return redirect(auth_url)

    except Exception as e:
        print(f"Login error: {e}")
        return redirect(url_for('index'))

@app.route("/callback")
def callback():
    try:
        flow.fetch_token(authorization_response=request.url)
        credentials = flow.credentials
        
        request_session = requests.session()
        cached_session = cachecontrol.CacheControl(request_session)
        token_request = google.auth.transport.requests.Request(session=cached_session)

        id_info = id_token.verify_oauth2_token(
            id_token=credentials.id_token,
            request=token_request,
            audience=GOOGLE_CLIENT_ID
        )
        
        session["google_id"] = id_info.get("sub")
        session["name"] = id_info.get("name")
        session["email"] = id_info.get("email")
        
        session['credentials'] = {
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes
        }
        
        return redirect(url_for("index"))
    except Exception as e:
        print(f"Callback error: {e}")
        return redirect(url_for("index"))

@app.route("/drive")
def drive():
    if 'credentials' not in session:
        return redirect(url_for('login'))

    credentials = google.oauth2.credentials.Credentials(**session['credentials'])
    drive_service = build('drive', 'v3', credentials=credentials)

    try:
        results = drive_service.files().list(
            pageSize=100,
            fields="nextPageToken, files(id, name, mimeType, modifiedTime, size)",
            orderBy="modifiedTime desc"
        ).execute()
        files = results.get('files', [])

        session['credentials'] = {
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes
        }

        return render_template('drive.html', files=files)
    except Exception as e:
        print(f"Drive error: {e}")
        return redirect(url_for("index"))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

if __name__ == "__main__":
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"  # Only for development
    app.run(debug=True)