# Startar Aktiebetyg-servern + Cloudflare-tunneln vid Windows-inloggning.
# Registrerad som schemalagd uppgift "AktiebetygStartup" (se README.md).
# OBS: den publika URL:en i cloudflared.log byts ut varje gång detta skript
# körs (gratis "quick tunnel" utan eget domännamn) - kolla loggen efter varje
# omstart för att se aktuell adress.

Set-Location "C:\Users\leoor\Documents\stock-rating-app"

Start-Process -FilePath "cmd.exe" -ArgumentList '/c python app.py > server.log 2>&1' -WindowStyle Hidden

Start-Sleep -Seconds 3

Start-Process -FilePath "cmd.exe" -ArgumentList '/c "C:\Program Files (x86)\cloudflared\cloudflared.exe" tunnel --url http://localhost:5000 > cloudflared.log 2>&1' -WindowStyle Hidden
