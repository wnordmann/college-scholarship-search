import os
import pandas as pd
import re

def clean_school_name(filename):
    """
    Extracts 'University of Alabama' from 'University_of_Alabama_table_0.csv'
    """
    # Remove the '_table_X.csv' suffix
    name = re.sub(r'_table_\d+\.csv$', '', filename)
    # Replace underscores with spaces
    return name.replace('_', ' ')

def aggregate_by_headers(input_dir='results', output_dir='aggregated_results'):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Dictionary to store groups: { tuple_of_headers: [list_of_dataframes] }
    header_groups = {}

    print(f"📂 Scanning {input_dir} for matching tables...")

    for filename in os.listdir(input_dir):
        if filename.endswith('.csv'):
            file_path = os.path.join(input_dir, filename)
            
            try:
                # Read the CSV
                df = pd.read_csv(file_path)
                
                # We use a tuple of sorted column names as a unique key for matching
                # We use lowercase/stripped names to ensure 'GPA' matches 'gpa '
                raw_headers = df.columns.tolist()
                normalized_headers = tuple(sorted([str(h).strip().lower() for h in raw_headers]))

                if not normalized_headers:
                    continue

                # Add the 'College' column from the filename
                school_name = clean_school_name(filename)
                df.insert(0, 'College', school_name)

                # Grouping logic
                if normalized_headers not in header_groups:
                    header_groups[normalized_headers] = []
                
                header_groups[normalized_headers].append(df)

            except Exception as e:
                print(f"⚠️ Could not process {filename}: {e}")

    # Merge and save the groups
    group_count = 0
    for headers, df_list in header_groups.items():
        if len(df_list) > 1:  # Only merge if there's more than one school in the group
            merged_df = pd.concat(df_list, ignore_index=True)
            
            # Create a preview of headers for the filename
            safe_header_preview = "_".join(list(headers)[:2]) # first two headers
            output_file = os.path.join(output_dir, f"group_{group_count}_{safe_header_preview}.csv")
            
            merged_df.to_csv(output_file, index=False)
            print(f"✅ Group {group_count}: Merged {len(df_list)} schools into {output_file}")
            group_count += 1
        else:
            # These are "orphans" - tables with unique layouts
            pass

    print(f"\n✨ Done! Found {group_count} distinct table layouts with multiple schools.")

if __name__ == "__main__":
    aggregate_by_headers()