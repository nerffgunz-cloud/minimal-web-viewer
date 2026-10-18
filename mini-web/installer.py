import os
import zipfile

def run_installer():
    downloads_dir = "downloads"
    base_local_dir = "local"
    
    print("=== MWB Local Package Installer ===")
    
    if not os.path.exists(downloads_dir):
        print(f"Error: '{downloads_dir}' directory does not exist.")
        return
        
    zip_files = [f for f in os.listdir(downloads_dir) if f.endswith('.zip')]
    
    if not zip_files:
        print(f"No .zip packages found in '{downloads_dir}/'. Download a package first!")
        return
        
    print("\nAvailable Packages:")
    for idx, zip_file in enumerate(zip_files, 1):
        print(f"  [{idx}] {zip_file}")
        
    choice = input("\nEnter package number to install (or 'q' to quit): ").strip()
    if choice.lower() == 'q':
        print("Installer exited.")
        return
        
    try:
        choice_idx = int(choice) - 1
        if 0 <= choice_idx < len(zip_files):
            selected_zip = zip_files[choice_idx]
            zip_path = os.path.join(downloads_dir, selected_zip)
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                namelist = zip_ref.namelist()
                
                # Check if dir.txt exists inside the zip package
                target_subdir = ""
                if "dir.txt" in namelist:
                    target_subdir = zip_ref.read("dir.txt").decode("utf-8").strip()
                
                # Construct final extraction path (e.g., local/wikipedia-clone/articles/)
                extract_to = os.path.join(base_local_dir, target_subdir)
                os.makedirs(extract_to, exist_ok=True)
                
                print(f"\nInstalling '{selected_zip}' into '{extract_to}'...")
                
                # Extract files, ignoring dir.txt itself
                for member in namelist:
                    if member == "dir.txt" or member.endswith('/'):
                        continue
                        
                    # Read file data from zip
                    source_file = zip_ref.open(member)
                    
                    # Target path for individual file inside the package
                    target_file_path = os.path.join(extract_to, member)
                    
                    # Ensure sub-directories inside the package are created if needed
                    os.makedirs(os.path.dirname(target_file_path), exist_ok=True)
                    
                    with open(target_file_path, "wb") as target_file:
                        target_file.write(source_file.read())
                        
            print("Installation complete! Your files are indexed and ready to search using '@'.")
        else:
            print("Error: Invalid package selection number.")
    except ValueError:
        print("Error: Please enter a valid number.")

if __name__ == "__main__":
    run_installer()