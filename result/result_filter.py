import os
import json
import shutil
def check_and_delete_folders():
    # Get current directory
    current_dir = os.getcwd()
    
    # Track deleted folders
    deleted_folders = []
    
    # Iterate through all folders in current directory
    for folder in os.listdir(current_dir):
        folder_path = os.path.join(current_dir, folder)
        
        # Check if it's a directory
        if os.path.isdir(folder_path):
            score_file = os.path.join(folder_path, 'score.json')
            
            # Check if score file exists
            if os.path.exists(score_file):
                try:
                    with open(score_file, 'r') as f:
                        data = json.load(f)
                        
                    # Check score value
                    if data.get('score') != 100:
                        # Delete the folder
                        shutil.rmtree(folder_path)
                        deleted_folders.append(folder)
                        
                except (json.JSONDecodeError, FileNotFoundError) as e:
                    print(f"Error reading {score_file}: {e}")
            else:
                shutil.rmtree(folder_path)
                deleted_folders.append(folder)

    # Print results
    if deleted_folders:
        print("Deleted folders:")
        for folder in deleted_folders:
            print(f"- {folder}")
    else:
        print("No folders needed to be deleted.")

# Run the function
if __name__ == "__main__":
    check_and_delete_folders()
