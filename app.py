import streamlit as st
import requests
import csv
import os

def fetch_all_pages(url):
    results = []
    while url:
        response = requests.get(url)
        if response.status_code != 200:
            return None
        results.extend(response.json())
        url = response.links.get('next', {}).get('url')
    return results

def get_github_data(username):
    base_url = f"https://api.github.com/users/{username}"
    followers_url = f"{base_url}/followers"
    following_url = f"{base_url}/following"
    
    followers = fetch_all_pages(followers_url)
    following = fetch_all_pages(following_url)
    
    if followers is not None and following is not None:
        followers_list = [follower['login'] for follower in followers]
        following_list = [followed['login'] for followed in following]
        
        return {
            'followers': followers_list,
            'following': following_list
        }
    else:
        return None

def save_to_csv(data, filename="github_data.csv"):
    filepath = os.path.join("data", filename)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['username', 'following', 'follower', 'link'])
        
        all_users = set(data['followers']) | set(data['following'])
        
        for user in all_users:
            following = 'Yes' if user in data['following'] else 'No'
            follower = 'Yes' if user in data['followers'] else 'No'
            writer.writerow([user, following, follower, f"https://github.com/{user}"])
    return filepath

def read_csv(filepath):
    data = []
    with open(filepath, mode='r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            data.append(row)
    return data

# Streamlit App
st.title("GitHub Follower and Following Checker")

username = st.text_input("Enter GitHub Username:")
csv_file = os.path.join("data", "github_data.csv")

if st.button("Fetch Data"):
    if username:
        data = get_github_data(username)
        if data:
            csv_file = save_to_csv(data)
            st.success(f"Data saved to {csv_file}")
            table_data = read_csv(csv_file)
            st.write("### Follower and Following Data")
            st.dataframe(table_data, use_container_width=True)  # Display data as a table with full width
        else:
            st.error("Failed to fetch data from GitHub API")
    else:
        st.warning("Please enter a username.")

# Show existing data if CSV file exists
if os.path.exists(csv_file):
    table_data = read_csv(csv_file)
    st.write("### Existing Follower and Following Data")
    st.dataframe([{k: v for k, v in row.items() if k != 'link'} for row in table_data], use_container_width=True)  # Display data as a table without 'link' column

    if st.button("Show Summary"):
        if os.path.exists(csv_file):
            table_data = read_csv(csv_file)
            following_count = sum(1 for row in table_data if row['following'] == 'Yes')
            followers_count = sum(1 for row in table_data if row['follower'] == 'Yes')
            not_following_back = [row for row in table_data if row['following'] == 'Yes' and row['follower'] == 'No']
            
            st.write(f"**Total Following:** {following_count}")
            st.write(f"**Total Followers:** {followers_count}")
            st.write(f"**Not Following Back:** {len(not_following_back)}")
            
            if not_following_back:
                st.write("### Users Not Following Back")
                st.dataframe(not_following_back, use_container_width=True)  # Display data of users not following back
        else:
            st.warning("No data available. Please fetch data first.")