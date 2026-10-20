import os
import zipfile
import shutil

def extract_single_zip(zip_path, base_local_dir):
    """Extracts a zip file while honoring any internal dir.txt for correct subdirectory routing."""
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        namelist = zip_ref.namelist()
        
        # Check if dir.txt exists inside the zip package
        target_subdir = ""
        if "dir.txt" in namelist:
            target_subdir = zip_ref.read("dir.txt").decode("utf-8").strip()
        
        # Construct final extraction path inside local/
        extract_to = os.path.join(base_local_dir, target_subdir)
        os.makedirs(extract_to, exist_ok=True)
        
        print(f"Installing '{os.path.basename(zip_path)}' into '{extract_to}'...")
        zip_ref.extractall(extract_to)

def run_installer():
    downloads_dir = "downloads"
    base_local_dir = "local"
    
    print("=== MWB Local Package Installer ===")
    
    if not os.path.exists(downloads_dir):
        print(f"Error: '{downloads_dir}' directory does not exist.")
        return
        
    try:
        items = sorted(os.listdir(downloads_dir))
    except Exception:
        items = []
        
    valid_choices = []
    
    print("\nAvailable Packages / Folders:")
    for item in items:
        item_path = os.path.join(downloads_dir, item)
        if item.endswith('.zip') or os.path.isdir(item_path):
            valid_choices.append(item_path)
            
    if not valid_choices:
        print(f"No .zip packages or folders found in '{downloads_dir}/'.")
        return
        
    for idx, path in enumerate(valid_choices, 1):
        label = "[Folder]" if os.path.isdir(path) else "[Zip]"
        print(f"  [{idx}] {label} {os.path.basename(path)}")
        
    choice = input("\nEnter number to install (or 'q' to quit): ").strip()
    if choice.lower() == 'q':
        print("Installer exited.")
        return

    try:
        choice_idx = int(choice) - 1
        if 0 <= choice_idx < len(valid_choices):
            selected_path = valid_choices[choice_idx]
            zip_files_to_install = []
            
            if os.path.isdir(selected_path):
                for root, dirs, files in os.walk(selected_path):
                    for file in files:
                        if file.endswith('.zip'):
                            zip_files_to_install.append(os.path.join(root, file))
            else:
                # Inspect the single zip file to see if it's a master container holding nested zips
                temp_staging = os.path.join(base_local_dir, "_temp_staging")
                if os.path.exists(temp_staging):
                    shutil.rmtree(temp_staging)
                os.makedirs(temp_staging, exist_ok=True)
                
                try:
                    with zipfile.ZipFile(selected_path, 'r') as zip_ref:
                        zip_ref.extractall(temp_staging)
                    
                    # Search inside staging for inner zips
                    nested_zips = []
                    for root, dirs, files in os.walk(temp_staging):
                        for file in files:
                            if file.endswith('.zip'):
                                nested_zips.append(os.path.join(root, file))
                    
                    if nested_zips:
                        print(f"\nDetected master container package with {len(nested_zips)} nested zip(s):")
                        for nz in nested_zips:
                            print(f"  - {os.path.basename(nz)}")
                            try:
                                # Extract each nested zip through the dir.txt router
                                extract_single_zip(nz, base_local_dir)
                            except Exception as e:
                                print(f"    -> Error extracting {os.path.basename(nz)}: {e}")
                                
                        zip_files_to_install.append(selected_path)
                    else:
                        # Normal single package (no nested zips); install it directly using dir.txt routing
                        extract_single_zip(selected_path, base_local_dir)
                        zip_files_to_install.append(selected_path)
                
                finally:
                    # Clean up temporary staging folder
                    if os.path.exists(temp_staging):
                        shutil.rmtree(temp_staging)

            # If it was a folder selection, handle its inner zips here
            successfully_installed = []
            if os.path.isdir(selected_path):
                for root, dirs, files in os.walk(selected_path):
                    for file in files:
                        if file.endswith('.zip'):
                            zip_path = os.path.join(root, file)
                            try:
                                extract_single_zip(zip_path, base_local_dir)
                                successfully_installed.append(zip_path)
                            except Exception as e:
                                print(f"Error installing {file}: {e}")
            else:
                successfully_installed.extend(zip_files_to_install)

            # Clean up source zip(s) only if user confirms 'y'
            if successfully_installed:
                unique_to_clean = list(set(successfully_installed))
                del_choice = input(f"\nDo you want to delete the successfully installed source zip file(s)? (y/n): ").strip().lower()
                if del_choice == 'y':
                    for zip_path in unique_to_clean:
                        try:
                            if os.path.exists(zip_path):
                                os.remove(zip_path)
                                print(f"Deleted: {zip_path}")
                        except Exception as e:
                            print(f"Error deleting {zip_path}: {e}")
                    print("Cleanup complete.")
                else:
                    print("Zip files kept in downloads folder.")
                    
            print("\nInstallation process finished! Files are ready to search using '@'.")
        else:
            print("Error: Invalid selection number.")
            
    except ValueError:
        print("Error: Please enter a valid number.")

if __name__ == "__main__":
    run_installer()
