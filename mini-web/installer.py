import os
import zipfile

def run_installer():
    downloads_dir = "downloads"
    base_local_dir = "local"
    
    print("=== MWB Local Package Installer ===")
    
    if not os.path.exists(downloads_dir):
        print(f"Error: '{downloads_dir}' directory does not exist.")
        return
        
    # Gather items directly inside downloads/ (both individual files and folders)
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
            
            # If the user picked a folder, recursively find all zips inside it and its subdirectories
            if os.path.isdir(selected_path):
                for root, dirs, files in os.walk(selected_path):
                    for file in files:
                        if file.endswith('.zip'):
                            zip_files_to_install.append(os.path.join(root, file))
                            
                if not zip_files_to_install:
                    print(f"No .zip packages found inside folder '{selected_path}' or its subdirectories.")
                    return
                    
                print(f"\nFound {len(zip_files_to_install)} package(s) inside folder '{os.path.basename(selected_path)}':")
                for z in zip_files_to_install:
                    print(f"  - {os.path.basename(z)}")
                    
                confirm = input("Install all of them? (y/n): ").strip().lower()
                if confirm != 'y':
                    print("Installation cancelled.")
                    return
            else:
                # If the user picked a single zip file
                zip_files_to_install.append(selected_path)
            
            # Process installation for all gathered zip files
            successfully_installed = []
            for zip_path in zip_files_to_install:
                try:
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
                                
                    print(f"Successfully installed: {zip_path}")
                    successfully_installed.append(zip_path)
                    
                except Exception as e:
                    print(f"Error installing {zip_path}: {e}")
            
            # ASK ONCE AND ONLY ONCE AT THE END
            if successfully_installed:
                del_choice = input(f"\nDo you want to delete the {len(successfully_installed)} successfully installed zip file(s)? (y/n): ").strip().lower()
                if del_choice == 'y':
                    for zip_path in successfully_installed:
                        try:
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
