# Streamlit UI

## Run
Install UI-only dependencies:
```
pip install -r requirements.txt
```

Ensure the API is running and `API_BASE_URL` points to it.

```
streamlit run frontend_streamlit/app.py
```

## Auth
Uses `/api/v1/auth/login` to obtain a bearer token. Token is stored in Streamlit session state.

## Pages
- Worklist
- Patient Detail
- Admin
