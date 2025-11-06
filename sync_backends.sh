# VPS 1 registriert VPS 2
curl -X POST http://72.61.185.109:5000/nodes/register \
  -H "Content-Type: application/json" \
  -d '{"node_address": "http://72.61.185.115:5000"}'

# VPS 2 registriert VPS 1
curl -X POST http://72.61.185.115:5000/nodes/register \
  -H "Content-Type: application/json" \
  -d '{"node_address": "http://72.61.185.109:5000"}'

curl http://72.61.185.109:5000/nodes/list
curl http://72.61.185.115:5000/nodes/list 