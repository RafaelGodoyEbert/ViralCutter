import os
import json

def save_viral_segments(segments_data=None):
    output_txt_file = "tmp/viral_segments.txt"

    # Check if file already exists
    if not os.path.exists(output_txt_file):
        if segments_data is None:
            # Request user to input JSON if file doesn't exist and segments are not defined
            while True:
                user_input = input("\nPlease enter the JSON in the desired format:\n")
                try:
                    # Try to load the inserted JSON
                    segments_data = json.loads(user_input)

                    # Validate if format is correct
                    if "segments" in segments_data and isinstance(segments_data["segments"], list):
                        # Save data to JSON file
                        with open(output_txt_file, 'w', encoding='utf-8') as file:
                            json.dump(segments_data, file, ensure_ascii=False, indent=4)
                        print(f"Viral segments saved to {output_txt_file}")
                        break
                    else:
                        print("Invalid format. Make sure the structure is correct.")
                except json.JSONDecodeError:
                    print("Error decoding JSON. Please check the formatting.")
                print("Please try again.")
        else:
            # If segments were generated, save automatically
            with open(output_txt_file, 'w', encoding='utf-8') as file:
                json.dump(segments_data, file, ensure_ascii=False, indent=4)
            print(f"Viral segments saved to {output_txt_file}\n")
    else:
        print(f"File {output_txt_file} already exists. No additional input needed.")