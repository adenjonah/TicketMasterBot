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

# Function to run the table creation script on an app
create_tables_app() {
  local app=$1
  echo "==== Creating tables for $app ===="
  
  # Upload the script to Heroku
  echo "Deploying create_server_table.py to $app..."
  git add create_server_table.py
  git commit -m "Add script to create server table if missing" --allow-empty
  git push https://git.heroku.com/$app.git HEAD:master
  
  # Run the script on Heroku
  echo "Running table creation script on $app..."
  heroku run python create_server_table.py --app $app
  
  echo "Table creation complete for $app!"
  echo ""
}

# Main script
echo "Starting table creation for all TM crawler apps..."

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
    create_tables_app "$app"
  done
else
  # Update selected apps
  for selection in "${selections[@]}"; do
    index=$((selection-1))
    if [ $index -ge 0 ] && [ $index -lt ${#apps[@]} ]; then
      create_tables_app "${apps[$index]}"
    else
      echo "Invalid selection: $selection"
    fi
  done
fi

echo "All requested table creations completed!" 