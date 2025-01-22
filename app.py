import streamlit as st
import requests
import csv
import os
import matplotlib.pyplot as plt
import seaborn as sns

@st.cache_data
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
    followers = fetch_all_pages(f"{base_url}/followers")
    following = fetch_all_pages(f"{base_url}/following")
    
    if followers is not None and following is not None:
        return {
            'followers': [f['login'] for f in followers],
            'following': [f['login'] for f in following]
        }
    return None

def save_to_csv(data, username):
    filename = f"github_data_{username}.csv"
    filepath = os.path.join("data", filename)
    if os.path.exists(filepath):
        os.remove(filepath)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['username', 'following', 'follower', 'link'])
        all_users = set(data['followers']) | set(data['following'])
        for user in all_users:
            writer.writerow([user, 'Yes' if user in data['following'] else 'No', 'Yes' if user in data['followers'] else 'No', f"https://github.com/{user}"])
    return filepath

def read_csv(filepath):
    with open(filepath, mode='r') as file:
        return list(csv.DictReader(file))

# Streamlit App
st.title("GitHub Follower and Following Checker")

username = st.text_input("Enter GitHub Username:")

if st.button("Fetch Data"):
    if username:
        data = get_github_data(username)
        if data:
            csv_file = save_to_csv(data, username)
            st.success(f"Data saved to {csv_file}")
            st.write(f"### Follower and Following Data of {username}")
            st.dataframe(read_csv(csv_file), use_container_width=True)
        else:
            st.error("Failed to fetch data from GitHub API")
    else:
        st.warning("Please enter a username.")

csv_file = os.path.join("data", f"github_data_{username}.csv")
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
        st.dataframe(not_following_back, use_container_width=True)

    # Pie chart for followers and following
    fig1, ax1 = plt.subplots()
    ax1.pie([following_count, followers_count], labels=['Following', 'Followers'], autopct='%1.1f%%', startangle=90)
    ax1.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
    st.pyplot(fig1)

    # Bar chart for users not following back
    fig2, ax2 = plt.subplots()
    sns.barplot(x=['Not Following Back', 'Following Back'], y=[len(not_following_back), following_count - len(not_following_back)], ax=ax2)
    ax2.set_ylabel('Count')
    st.pyplot(fig2)
        
    st.download_button(
        label="Download CSV",
        data=open(csv_file, 'rb').read(),
        file_name=f"github_data_{username}.csv",
        mime="text/csv"
    )
