import streamlit as st
import requests
import csv
import os
import matplotlib.pyplot as plt
import seaborn as sns
import glob
import pandas as pd

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

def get_user_profile(username, token=None):
    """Fetch detailed profile information for a given username"""
    headers = {'Authorization': f'token {token}'} if token else {}
    url = f"https://api.github.com/users/{username}"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    return None

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

def save_to_csv(data, username, token=None):
    filename = f"github_data_{username}.csv"
    filepath = os.path.join("data", filename)
    if os.path.exists(filepath):
        os.remove(filepath)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    
    # Fetch profile information for each user
    with open(filepath, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['username', 'following', 'follower', 'link', 'avatar_url', 'name', 'bio', 'public_repos', 'location'])
        all_users = set(data['followers']) | set(data['following'])
        
        # Show progress bar while fetching user data
        progress_bar = st.progress(0)
        for i, user in enumerate(all_users):
            profile = get_user_profile(user, token)
            if profile:
                writer.writerow([
                    user,
                    'Yes' if user in data['following'] else 'No',
                    'Yes' if user in data['followers'] else 'No',
                    f"https://github.com/{user}",
                    profile.get('avatar_url', ''),
                    profile.get('name', ''),
                    profile.get('bio', ''),
                    profile.get('public_repos', 0),
                    profile.get('location', '')
                ])
            else:
                writer.writerow([user, 'Yes' if user in data['following'] else 'No', 'Yes' if user in data['followers'] else 'No', f"https://github.com/{user}", '', '', '', 0, ''])
            
            # Update progress bar
            progress_bar.progress((i + 1) / len(all_users))
        
        progress_bar.empty()
    
    return filepath


def read_csv(filepath):
    with open(filepath, mode='r') as file:
        return list(csv.DictReader(file))

def get_existing_csv_files():
    return glob.glob("data/github_data_*.csv")

def show_overview_tab(table_data, current_username):
    following_count = sum(1 for row in table_data if row['following'] == 'Yes')
    followers_count = sum(1 for row in table_data if row['follower'] == 'Yes')
    not_following_back = [row for row in table_data if row['following'] == 'Yes' and row['follower'] == 'No']
    
    metrics_col1, metrics_col2, metrics_col3, metrics_col4 = st.columns(4)
    with metrics_col1:
        st.metric("Following", following_count)
    with metrics_col2:
        st.metric("Followers", followers_count)
    with metrics_col3:
        st.metric("Not Following Back", len(not_following_back))
    with metrics_col4:
        if following_count > 0:
            st.metric("Followers/Following Ratio", f"{(followers_count / following_count):.2f}")
    
    # Add profile cards view option
    view_type = st.radio("Select View", ["Table", "Profile Cards"], horizontal=True)
    
    if view_type == "Table":
        st.dataframe(table_data, use_container_width=True)
    else:
        # Display profile cards in a grid
        cols = st.columns(3)
        for idx, user in enumerate(table_data):
            with cols[idx % 3]:
                with st.container():
                    st.markdown(
                        f"""
                        <div style="padding: 1rem; border: 1px solid #ddd; border-radius: 8px; margin-bottom: 1rem">
                            <div style="display: flex; align-items: center; margin-bottom: 10px">
                                <img src="{user['avatar_url']}" style="width: 60px; height: 60px; border-radius: 50%; margin-right: 10px">
                                <div>
                                    <h3 style="margin: 0">{user['username']}</h3>
                                    <p style="margin: 0; color: #666">{user['name'] or ''}</p>
                                </div>
                            </div>
                            <p style="margin: 5px 0">{user['bio'] or ''}</p>
                            <p style="margin: 5px 0">📍 {user['location'] or 'No location'}</p>
                            <p style="margin: 5px 0">📚 {user['public_repos']} public repos</p>
                            <p style="margin: 5px 0">Status: {' • '.join(filter(None, [
                                'Following' if user['following'] == 'Yes' else None,
                                'Follower' if user['follower'] == 'Yes' else None
                            ]))}</p>
                            <a href="{user['link']}" target="_blank">View Profile</a>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
    
    st.download_button(
        label="Download CSV",
        data=open(st.session_state.current_file, 'rb').read(),
        file_name=f"github_data_{current_username}.csv",
        mime="text/csv"
    )

def show_not_following_back_tab(table_data):
    not_following_back = [row for row in table_data if row['following'] == 'Yes' and row['follower'] == 'No']
    
    st.write("### Users Not Following Back")
    
    # Display profile cards in a grid
    cols = st.columns(3)
    for idx, user in enumerate(not_following_back):
        with cols[idx % 3]:
            with st.container():
                st.markdown(
                    f"""
                    <div style="padding: 1rem; border: 1px solid #ddd; border-radius: 8px; margin-bottom: 1rem">
                        <div style="display: flex; align-items: center; margin-bottom: 10px">
                            <img src="{user['avatar_url']}" style="width: 60px; height: 60px; border-radius: 50%; margin-right: 10px">
                            <div>
                                <h3 style="margin: 0">{user['username']}</h3>
                                <p style="margin: 0; color: #666">{user['name'] or ''}</p>
                            </div>
                        </div>
                        <p style="margin: 5px 0">{user['bio'] or ''}</p>
                        <p style="margin: 5px 0">📍 {user['location'] or 'No location'}</p>
                        <p style="margin: 5px 0">📚 {user['public_repos']} public repos</p>
                        <p style="margin: 5px 0">Status: Following but not following back</p>
                        <a href="{user['link']}" target="_blank">View Profile</a>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

def show_visualizations_tab(table_data):
    st.write("## GitHub Network Analytics")
    
    # Calculate metrics
    following_count = sum(1 for row in table_data if row['following'] == 'Yes')
    followers_count = sum(1 for row in table_data if row['follower'] == 'Yes')
    mutual_followers = sum(1 for row in table_data if row['following'] == 'Yes' and row['follower'] == 'Yes')
    not_following_back = [row for row in table_data if row['following'] == 'Yes' and row['follower'] == 'No']
    
    # Network Health Metrics
    st.write("### 📊 Network Health Metrics")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        engagement_rate = (mutual_followers / following_count * 100) if following_count > 0 else 0
        st.metric("Engagement Rate", f"{engagement_rate:.1f}%", 
                 help="Percentage of mutual connections among people you follow")
    with col2:
        reciprocity = (mutual_followers / len(table_data) * 100) if len(table_data) > 0 else 0
        st.metric("Network Reciprocity", f"{reciprocity:.1f}%",
                 help="Percentage of mutual connections in your entire network")
    with col3:
        influence_ratio = (followers_count / following_count) if following_count > 0 else 0
        st.metric("Influence Ratio", f"{influence_ratio:.2f}",
                 help="Ratio of followers to following (>1 indicates high influence)")
    with col4:
        network_size = len(table_data)
        st.metric("Network Size", network_size,
                 help="Total number of unique connections")

    # Location Analysis
    st.write("### 🌍 Geographic Distribution")
    location_data = {}
    for row in table_data:
        if row['location']:
            location_data[row['location']] = location_data.get(row['location'], 0) + 1
    
    if location_data:
        fig_loc = plt.figure(figsize=(10, 6))
        locations = list(location_data.keys())
        counts = list(location_data.values())
        plt.bar(locations[:10], counts[:10], color=sns.color_palette("viridis", 10))
        plt.xticks(rotation=45, ha='right')
        plt.title("Top 10 Locations in Your Network")
        plt.tight_layout()
        st.pyplot(fig_loc)

    # Repository Analysis
    st.write("### 📚 Repository Distribution")
    col1, col2 = st.columns(2)
    
    with col1:
        # Create repository distribution histogram
        fig_repos = plt.figure(figsize=(8, 5))
        plt.hist([int(row['public_repos']) for row in table_data], 
                bins=20, color='skyblue', edgecolor='black')
        plt.title("Distribution of Public Repositories")
        plt.xlabel("Number of Public Repos")
        plt.ylabel("Frequency")
        st.pyplot(fig_repos)
    
    with col2:
        # Calculate and display repository statistics
        repo_counts = [int(row['public_repos']) for row in table_data]
        repo_stats = {
            "Mean": f"{sum(repo_counts) / len(repo_counts):.1f}",
            "Median": f"{sorted(repo_counts)[len(repo_counts)//2]}",
            "Max": max(repo_counts),
            "Min": min(repo_counts)
        }
        
        st.write("Repository Statistics")
        st.table(pd.DataFrame([repo_stats]))

    # Network Composition Analysis
    st.write("### 🔄 Network Composition")
    
    # Create Sankey diagram data
    mutual = sum(1 for row in table_data if row['following'] == 'Yes' and row['follower'] == 'Yes')
    only_following = sum(1 for row in table_data if row['following'] == 'Yes' and row['follower'] == 'No')
    only_followers = sum(1 for row in table_data if row['following'] == 'No' and row['follower'] == 'Yes')

    # Mermaid diagram for network flow
    st.markdown("""
    ```mermaid
    sankey-beta
    Your Network,Mutual Connections,{mutual}
    Your Network,Only Following,{only_following}
    Your Network,Only Followers,{only_followers}
    ```
    """.format(mutual=mutual, only_following=only_following, only_followers=only_followers))

    # Activity Analysis
    st.write("### 📈 Most Active Users in Your Network")
    
    # Sort users by repository count
    active_users = sorted(table_data, key=lambda x: int(x['public_repos']), reverse=True)[:5]
    
    fig_active = plt.figure(figsize=(10, 5))
    plt.bar([row['username'] for row in active_users], 
            [int(row['public_repos']) for row in active_users],
            color=sns.color_palette("husl", 5))
    plt.xticks(rotation=45, ha='right')
    plt.title("Top 5 Most Active Users (by Public Repos)")
    plt.tight_layout()
    st.pyplot(fig_active)

    # Export Options
    st.write("### 📤 Export Analytics")
    
    # Create a summary DataFrame
    summary_data = {
        "Metric": ["Network Size", "Following", "Followers", "Mutual Connections", 
                  "Engagement Rate", "Influence Ratio", "Most Common Location"],
        "Value": [network_size, following_count, followers_count, mutual_followers,
                 f"{engagement_rate:.1f}%", f"{influence_ratio:.2f}", 
                 max(location_data.items(), key=lambda x: x[1])[0] if location_data else "N/A"]
    }
    summary_df = pd.DataFrame(summary_data)
    
    # Convert DataFrame to CSV
    csv = summary_df.to_csv(index=False)
    st.download_button(
        label="Download Analytics Summary",
        data=csv,
        file_name="github_network_analytics.csv",
        mime="text/csv"
    )

# Streamlit App
st.set_page_config(layout="wide", page_title="GitHub Followers Analyzer")
st.title("GitHub Followers Analyzer")

# Sidebar controls
with st.sidebar:
    st.header("Load Existing Data")
    existing_files = get_existing_csv_files()
    if existing_files:
        selected_file = st.selectbox(
            "Select a previously analyzed profile:",
            options=existing_files,
            format_func=lambda x: os.path.basename(x).replace('github_data_', '').replace('.csv', ''),
            key="existing_data"
        )
        if st.button("Load Selected Profile"):
            st.session_state.current_file = selected_file
    else:
        st.info("No analyzed profiles found. Use the form below to analyze a new profile.")

    st.markdown("---")
    
    st.header("Analyze New Profile")
    username = st.text_input("Enter GitHub Username:")
    token = st.text_input("Enter GitHub Token (optional):", type="password")
    
    if st.button("Fetch Data"):
        if username:
            with st.spinner('Fetching data from GitHub...'):
                data = get_github_data(username, token)
                if data:
                    csv_file = save_to_csv(data, username)
                    st.success(f"Data saved for {username}")
                    st.session_state.current_file = csv_file
                else:
                    st.error("Failed to fetch data from GitHub API. Try using a token to get more requests.")
        else:
            st.warning("Please enter a username.")

# Main content area with tabs
if 'current_file' in st.session_state and os.path.exists(st.session_state.current_file):
    table_data = read_csv(st.session_state.current_file)
    current_username = os.path.basename(st.session_state.current_file).replace('github_data_', '').replace('.csv', '')
    
    st.write(f"### Analysis Results for {current_username}")
    
    tab1, tab2, tab3 = st.tabs(["Overview", "Not Following Back", "Visualizations"])
    
    with tab1:
        show_overview_tab(table_data, current_username)
    
    with tab2:
        show_not_following_back_tab(table_data)
    
    with tab3:
        show_visualizations_tab(table_data)