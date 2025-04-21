#!/bin/bash

# List of Heroku apps to update
apps=(
  "tm-bot-and-crawler-east"
  "tm-crawler-canada"
  "tm-crawler-comedy"
  "tm-crawler-south-and-mexico"
  "tm-crawler-west"
  "tm-scraper-europe"
)

# Function to deploy and run the schema update on an app
update_schema() {
  local app=$1
  echo "==== Updating schema for $app ===="
  
  # Deploy the latest code to the app
  echo "Deploying latest code to $app..."
  git push https://git.heroku.com/$app.git HEAD:master
  
  # Run the schema update script
  echo "Running schema update on $app..."
  heroku run python database/schema_update.py --app $app
  
  # Restart the app to apply changes
  echo "Restarting $app to apply changes..."
  heroku ps:restart --app $app
  
  echo "Schema update complete for $app!"
  echo ""
}

# Main script
echo "Starting schema update for all TM crawler apps..."

# Ask which apps to update
echo "Which apps do you want to update?"
echo "0) All apps"
for i in "${!apps[@]}"; do
  echo "$((i+1))) ${apps[$i]}"
done
echo "Enter the number(s) separated by space, or 0 for all:"
read -a selections

if [[ "${selections[*]}" =~ "0" ]]; then
  # Update all apps
  for app in "${apps[@]}"; do
    update_schema "$app"
  done
else
  # Update selected apps
  for selection in "${selections[@]}"; do
    index=$((selection-1))
    if [ $index -ge 0 ] && [ $index -lt ${#apps[@]} ]; then
      update_schema "${apps[$index]}"
    else
      echo "Invalid selection: $selection"
    fi
  done
fi

echo "All schema updates completed!" 