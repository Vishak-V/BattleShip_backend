
docker-compose up -d
Start-Sleep -Seconds 2  # Wait for containers to start
docker-compose logs -f
