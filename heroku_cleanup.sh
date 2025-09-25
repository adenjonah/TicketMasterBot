#!/bin/bash

# List of Heroku apps to clean up
apps=(
  "tm-bot-and-crawler-east"
  "tm-crawler-canada"
  "tm-crawler-comedy"
  "tm-crawler-south-and-mexico"
  "tm-crawler-west"
  "tm-scraper-europe"
)

# Function to run the cleanup script on an app
cleanup_app() {
  local app=$1
  echo "==== Cleaning up $app ===="
  
  # Upload the drop_legacy_servers.py script to Heroku
  echo "Deploying drop_legacy_servers.py to $app..."
  git add drop_legacy_servers.py
  git commit -m "Add script to remove legacy server IDs" --allow-empty
  git push https://git.heroku.com/$app.git HEAD:master
  
  # Run the cleanup script on Heroku
  echo "Running cleanup script on $app..."
  heroku run python drop_legacy_servers.py --app $app
  
  echo "Cleanup complete for $app!"
  echo ""
}

# Main script
echo "Starting cleanup of all TM crawler apps..."

# Ask which apps to clean up
echo "Which apps do you want to clean up?"
echo "0) All apps"
for i in "${!apps[@]}"; do
  echo "$((i+1))) ${apps[$i]}"
done
echo "Enter the number(s) separated by space, or 0 for all:"
read -a selections

if [[ "${selections[*]}" =~ "0" ]]; then
  # Clean up all apps
  for app in "${apps[@]}"; do
    cleanup_app "$app"
  done
else
  # Clean up selected apps
  for selection in "${selections[@]}"; do
    index=$((selection-1))
    if [ $index -ge 0 ] && [ $index -lt ${#apps[@]} ]; then
      cleanup_app "${apps[$index]}"
    else
      echo "Invalid selection: $selection"
    fi
  done
fi

echo "All requested cleanups completed!" 