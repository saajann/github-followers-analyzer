import streamlit as st
import requests
import csv
import os
import matplotlib.pyplot as plt
import seaborn as sns
import glob

@st.cache_data
def fetch_all_pages(url, headers):
    results = []
    while url:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            return None
        results.extend(response.json())
        url = response.links.get('next', {}).get('url')
    return results

def get_github_data(username, token=None):
    headers = {'Authorization': f'token {token}'} if token else {}
    base_url = f"https://api.github.com/users/{username}"
    followers = fetch_all_pages(f"{base_url}/followers", headers)
    following = fetch_all_pages(f"{base_url}/following", headers)
    
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

def get_existing_csv_files():
    return glob.glob("data/github_data_*.csv")

# Streamlit App
st.set_page_config(layout="wide", page_title="GitHub Followers Analyzer")
st.title("GitHub Followers Analyzer")

# Add file selector for existing CSV files
existing_files = get_existing_csv_files()
if existing_files:
    st.write("### Load Existing Data")
    selected_file = st.selectbox(
        "Select existing data file:",
        options=existing_files,
        format_func=lambda x: os.path.basename(x).replace('github_data_', '').replace('.csv', '')
    )

# Input for new username and token
st.write("### Fetch New Data")
username = st.text_input("Enter GitHub Username:")
token = st.text_input("Enter GitHub Token (optional):", type="password")

if st.button("Fetch Data"):
    if username:
        with st.spinner('Fetching data from GitHub...'):
            data = get_github_data(username, token)
            if data:
                csv_file = save_to_csv(data, username)
                st.success(f"Data saved to {csv_file}")
                selected_file = csv_file  # Automatically select newly created file
            else:
                st.error("Failed to fetch data from GitHub API, enter a token to get more requests.")
    else:
        st.warning("Please enter a username.")

# Process and display data
if 'selected_file' in locals() and os.path.exists(selected_file):
    table_data = read_csv(selected_file)
    current_username = os.path.basename(selected_file).replace('github_data_', '').replace('.csv', '')
    
    st.write(f"### Follower and Following Data of {current_username}")
    st.dataframe(table_data, use_container_width=True)
    
    following_count = sum(1 for row in table_data if row['following'] == 'Yes')
    followers_count = sum(1 for row in table_data if row['follower'] == 'Yes')
    not_following_back = [row for row in table_data if row['following'] == 'Yes' and row['follower'] == 'No']
    mutual_followers = [row for row in table_data if row['following'] == 'Yes' and row['follower'] == 'Yes']
    
    st.write(f"**Total Following:** {following_count}")
    st.write(f"**Total Followers:** {followers_count}")
    st.write(f"**Not Following Back:** {len(not_following_back)}")
    st.write(f"**Mutual Followers:** {len(mutual_followers)}")
    
    if following_count > 0:
        ratio = followers_count / following_count
        st.write(f"**Followers/Following Ratio:** {ratio:.2f}")
    
    with st.expander("Show Detailed Stats"):
        st.write("### Users Not Following Back")
        
        html_table = "<table><tr><th>Username</th><th>Link</th></tr>"
        for row in not_following_back:
            html_table += f"<tr><td>{row['username']}</td><td><a href='{row['link']}' target='_blank'>Open Profile</a></td></tr>"
        html_table += "</table>"
        
        st.markdown(html_table, unsafe_allow_html=True)
        
        st.write("### Mutual Followers")
        st.dataframe(mutual_followers, use_container_width=True)
    
    # Plots
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("### Followers vs Following")
        fig1, ax1 = plt.subplots()
        sns.barplot(x=['Following', 'Followers'], y=[following_count, followers_count], ax=ax1, palette="viridis")
        ax1.set_ylabel('Count')
        st.pyplot(fig1)
    
    with col2:
        st.write("### Following Back vs Not Following Back")
        not_following_back_count = len(not_following_back)
        following_back_count = following_count - not_following_back_count
        fig2, ax2 = plt.subplots()
        ax2.pie([not_following_back_count, following_back_count], labels=['Not Following Back', 'Following Back'], autopct='%1.1f%%', startangle=90, colors=['#ff9999','#66b3ff'])
        ax2.axis('equal')
        st.pyplot(fig2)
    
    st.write("### Mutual Followers vs Not Mutual")
    mutual_count = len(mutual_followers)
    non_mutual_count = following_count - mutual_count
    fig3, ax3 = plt.subplots()
    sns.barplot(x=[mutual_count, non_mutual_count], y=['Mutual Followers', 'Non-Mutual Followers'], ax=ax3, palette="magma")
    ax3.set_xlabel('Count')
    st.pyplot(fig3)
    
    st.download_button(
        label="Download CSV",
        data=open(selected_file, 'rb').read(),
        file_name=f"github_data_{current_username}.csv",
        mime="text/csv"
    )