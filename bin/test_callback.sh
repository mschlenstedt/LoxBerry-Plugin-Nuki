#!/bin/bash


post_data()
{
  cat <<EOF
{"deviceType": 0, "nukiId": 123456789, "mode": 2, "state": 3, "stateName": "unlocked", "batteryCritical": false}
EOF
}



curl -i \
-H "Accept: application/json" \
-H "Content-Type:application/json" \
-X POST --data "$(post_data)" "http://localhost:80/plugins/nukismartlock/callback.php?lbuid=54321" 

