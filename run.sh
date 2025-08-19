npm run dev &

(
    ./oauth.sh
) &

(
    source ./venv/bin/activate
    cd backend
    python main.py
) &

