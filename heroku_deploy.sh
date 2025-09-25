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

# Function to deploy to an app
deploy_app() {
  local app=$1
  echo "==== Deploying to $app ===="
  
  # Push to Heroku
  echo "Pushing latest changes to $app..."
  git push https://git.heroku.com/$app.git HEAD:master
  
  # Restart the app to apply changes
  echo "Restarting $app to apply changes..."
  heroku ps:restart --app $app
  
  echo "Deployment complete for $app!"
  echo ""
}

# Main script
echo "Starting deployment to all TM crawler apps..."

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
    deploy_app "$app"
  done
else
  # Update selected apps
  for selection in "${selections[@]}"; do
    index=$((selection-1))
    if [ $index -ge 0 ] && [ $index -lt ${#apps[@]} ]; then
      deploy_app "${apps[$index]}"
    else
      echo "Invalid selection: $selection"
    fi
  done
fi

echo "All deployments completed!" 