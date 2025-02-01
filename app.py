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
        with st.spinner('Fetching data from GitHub...'):
            data = get_github_data(username)
            if data:
                csv_file = save_to_csv(data, username)
                st.success(f"Data saved to {csv_file}")
                st.write(f"### Follower and Following Data of {username}")
                table_data = read_csv(csv_file)
                st.dataframe(table_data, use_container_width=True)
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
    mutual_followers = [row for row in table_data if row['following'] == 'Yes' and row['follower'] == 'Yes']
    
    st.write(f"**Total Following:** {following_count}")
    st.write(f"**Total Followers:** {followers_count}")
    st.write(f"**Not Following Back:** {len(not_following_back)}")
    st.write(f"**Mutual Followers:** {len(mutual_followers)}")
    
    # Rapporto Followers/Following
    if following_count > 0:
        ratio = followers_count / following_count
        st.write(f"**Followers/Following Ratio:** {ratio:.2f}")
    
    # Sezione Espandibile per Dettagli
    with st.expander("Show Detailed Stats"):
        st.write("### Users Not Following Back")
        st.dataframe(not_following_back, use_container_width=True)
        
        st.write("### Mutual Followers")
        st.dataframe(mutual_followers, use_container_width=True)
    
    # Grafici
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
    
    # Grafico a Barre Orizzontali per Mutual Followers
    st.write("### Mutual Followers vs Not Mutual")
    mutual_count = len(mutual_followers)
    non_mutual_count = following_count - mutual_count
    fig3, ax3 = plt.subplots()
    sns.barplot(x=[mutual_count, non_mutual_count], y=['Mutual Followers', 'Non-Mutual Followers'], ax=ax3, palette="magma")
    ax3.set_xlabel('Count')
    st.pyplot(fig3)
    
    # Pulsante per il Download del CSV
    st.download_button(
        label="Download CSV",
        data=open(csv_file, 'rb').read(),
        file_name=f"github_data_{username}.csv",
        mime="text/csv"
    )