import streamlit as st
import requests
import os
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import sqlite3
from datetime import datetime
import numpy as np
import plotly.express as px

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

def initialize_database():
    """Initialize SQLite database with necessary tables"""
    # Ensure the data directory exists
    os.makedirs("data", exist_ok=True)
    
    # Connect to the database (will create it if it doesn't exist)
    conn = sqlite3.connect('data/github_followers.db')
    cursor = conn.cursor()
    
    # Create main_users table to store the users we've analyzed
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS main_users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        last_updated TIMESTAMP
    )
    ''')
    
    # Create connections table to store follower/following relationships
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS github_users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        name TEXT,
        bio TEXT,
        avatar_url TEXT,
        location TEXT,
        public_repos INTEGER,
        last_updated TIMESTAMP
    )
    ''')
    
    # Create connections table to store follower/following relationships
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS connections (
        main_user TEXT,
        related_user TEXT,
        is_following BOOLEAN,
        is_follower BOOLEAN,
        last_updated TIMESTAMP,
        PRIMARY KEY (main_user, related_user)
    )
    ''')
    
    conn.commit()
    conn.close()

def save_to_database(data, username, token=None):
    """Save GitHub data to SQLite database"""
    conn = sqlite3.connect('data/github_followers.db')
    cursor = conn.cursor()
    
    # Update or insert the main user
    current_time = datetime.now().isoformat()
    cursor.execute('''
    INSERT OR REPLACE INTO main_users (username, last_updated)
    VALUES (?, ?)
    ''', (username, current_time))
    
    # Get all users (followers and following)
    all_users = set(data['followers']) | set(data['following'])
    
    # Show progress bar while fetching user data
    progress_bar = st.progress(0)
    
    for i, user in enumerate(all_users):
        # Fetch profile information
        profile = get_user_profile(user, token)
        
        if profile:
            # Insert or update user data
            cursor.execute('''
            INSERT OR REPLACE INTO github_users 
            (username, name, bio, avatar_url, location, public_repos, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                user,
                profile.get('name', ''),
                profile.get('bio', ''),
                profile.get('avatar_url', ''),
                profile.get('location', ''),
                profile.get('public_repos', 0),
                current_time
            ))
        else:
            # Insert with minimal data if profile fetch failed
            cursor.execute('''
            INSERT OR REPLACE INTO github_users 
            (username, last_updated)
            VALUES (?, ?)
            ''', (user, current_time))
        
        # Insert or update connection data
        cursor.execute('''
        INSERT OR REPLACE INTO connections
        (main_user, related_user, is_following, is_follower, last_updated)
        VALUES (?, ?, ?, ?, ?)
        ''', (
            username,
            user,
            user in data['following'],
            user in data['followers'],
            current_time
        ))
        
        # Update progress bar
        progress_bar.progress((i + 1) / len(all_users))
    
    conn.commit()
    conn.close()
    progress_bar.empty()
    
    return True

def get_analyzed_users():
    """Get list of users that have been analyzed"""
    conn = sqlite3.connect('data/github_followers.db')
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT username, last_updated FROM main_users
    ORDER BY last_updated DESC
    ''')
    
    users = cursor.fetchall()
    conn.close()
    
    return users

def get_user_connections(username):
    """Get connections data for a specific user"""
    conn = sqlite3.connect('data/github_followers.db')
    conn.row_factory = sqlite3.Row  # This enables column access by name
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT 
        c.related_user as username,
        c.is_following as following,
        c.is_follower as follower,
        u.name,
        u.bio,
        u.avatar_url,
        u.location,
        u.public_repos,
        'https://github.com/' || c.related_user as link
    FROM connections c
    JOIN github_users u ON c.related_user = u.username
    WHERE c.main_user = ?
    ''', (username,))
    
    connections = [dict(row) for row in cursor.fetchall()]
    
    # Convert boolean integers to 'Yes'/'No' strings for consistency with previous code
    for conn_data in connections:
        conn_data['following'] = 'Yes' if conn_data['following'] else 'No'
        conn_data['follower'] = 'Yes' if conn_data['follower'] else 'No'
    
    conn.close()
    return connections

def export_connections_to_csv(username):
    """Export connections data to CSV"""
    connections = get_user_connections(username)
    df = pd.DataFrame(connections)
    
    csv = df.to_csv(index=False)
    return csv

def show_overview_tab(connections_data, current_username):
    following_count = sum(1 for row in connections_data if row['following'] == 'Yes')
    followers_count = sum(1 for row in connections_data if row['follower'] == 'Yes')
    not_following_back = [row for row in connections_data if row['following'] == 'Yes' and row['follower'] == 'No']
    
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
        st.dataframe(connections_data, use_container_width=True)
    else:
        # Display profile cards in a grid
        cols = st.columns(3)
        for idx, user in enumerate(connections_data):
            with cols[idx % 3]:
                # Determine card color based on follow status
                card_color = "#FFFFFF"  # Default white (they follow you, you don't follow them)
                if user['following'] == 'Yes' and user['follower'] == 'No':
                    card_color = "#FFCCCC"  # Red (you follow them, they don't follow back)
                elif user['following'] == 'Yes' and user['follower'] == 'Yes':
                    card_color = "#CCFFCC"  # Green (mutual follow)
                
                with st.container():
                    st.markdown(
                        f"""
                        <div style="padding: 1rem; border: 1px solid #ddd; border-radius: 8px; margin-bottom: 1rem; background-color: {card_color};">
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
    
    # Export to CSV option
    csv_data = export_connections_to_csv(current_username)
    st.download_button(
        label="Download CSV",
        data=csv_data,
        file_name=f"github_data_{current_username}.csv",
        mime="text/csv"
    )

def show_not_following_back_tab(connections_data):
    not_following_back = [row for row in connections_data if row['following'] == 'Yes' and row['follower'] == 'No']
    
    st.write("### Users Not Following Back")
    
    # Display profile cards in a grid
    cols = st.columns(3)
    for idx, user in enumerate(not_following_back):
        with cols[idx % 3]:
            with st.container():
                st.markdown(
                    f"""
                    <div style="padding: 1rem; border: 1px solid #ddd; border-radius: 8px; margin-bottom: 1rem; background-color: #FFCCCC;">
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

def show_visualizations_tab(connections_data):
    st.write("## GitHub Network Analytics")
    
    # Calculate core metrics
    following_count = sum(1 for row in connections_data if row['following'] == 'Yes')
    followers_count = sum(1 for row in connections_data if row['follower'] == 'Yes')
    mutual_followers = sum(1 for row in connections_data if row['following'] == 'Yes' and row['follower'] == 'Yes')
    
    # Network Health Metrics - Simple key metrics
    st.write("### 📊 Network Overview")
    col1, col2, col3 = st.columns(3)
    with col1:
        network_size = len(connections_data)
        st.metric("Network Size", network_size,
                 help="Total number of unique connections")
    with col2:
        influence_ratio = (followers_count / following_count) if following_count > 0 else 0
        st.metric("Influence Ratio", f"{influence_ratio:.2f}",
                 help="Ratio of followers to following (>1 indicates high influence)")
    with col3:
        engagement_rate = (mutual_followers / following_count * 100) if following_count > 0 else 0
        st.metric("Engagement Rate", f"{engagement_rate:.1f}%", 
                 help="Percentage of mutual connections among people you follow")

    # Network Composition - Simple pie chart
    st.write("### 🔄 Network Composition")
    
    mutual = sum(1 for row in connections_data if row['following'] == 'Yes' and row['follower'] == 'Yes')
    only_following = sum(1 for row in connections_data if row['following'] == 'Yes' and row['follower'] == 'No')
    only_followers = sum(1 for row in connections_data if row['following'] == 'No' and row['follower'] == 'Yes')
    
    network_fig = px.pie(
        names=['Mutual Connections', 'Only Following', 'Only Followers'],
        values=[mutual, only_following, only_followers],
        color_discrete_sequence=['#4CAF50', '#FFC107', '#2196F3'],
        hole=0.4
    )
    network_fig.update_layout(title="Network Connection Types")
    st.plotly_chart(network_fig, use_container_width=True)
    
    # Top Users You Follow But Don't Follow Back - Simple bar chart
    st.write("### 👥 Top Users You Follow (Not Following Back)")
    
    # Get users you follow but don't follow you back
    not_following_back = [row for row in connections_data if row['following'] == 'Yes' and row['follower'] == 'No']
    
    # Sort by public repos count instead of followers (since we have this data)
    if not_following_back:
        # Sort by public repos count to show most active first
        top_not_following = sorted(not_following_back, 
                                 key=lambda x: int(x.get('public_repos', 0)), 
                                 reverse=True)[:10]  # Top 10
        
        if top_not_following:
            usernames = [row.get('username', 'Unknown') for row in top_not_following]
            repo_counts = [int(row.get('public_repos', 0)) for row in top_not_following]
            
            fig = px.bar(
                x=usernames,
                y=repo_counts,
                labels={'x': 'Username', 'y': 'Public Repositories'},
                title="Top Users You Follow But Don't Follow You Back (by public repos)",
                color_discrete_sequence=['#FF5722']
            )
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)
    
    # Location Map - Simple visualization of follower locations
    st.write("### 🌍 Where Your Network Is Located")
    
    # Count locations
    location_data = {}
    for row in connections_data:
        if row.get('location'):
            location_data[row['location']] = location_data.get(row['location'], 0) + 1
    
    if location_data:
        # Sort by count and get top locations
        location_items = sorted(location_data.items(), key=lambda x: x[1], reverse=True)[:8]
        locations, counts = zip(*location_items) if location_items else ([], [])
        
        fig_loc = px.bar(
            x=locations, 
            y=counts,
            labels={'x': 'Location', 'y': 'Number of Connections'},
            title="Top Locations in Your Network",
            color_discrete_sequence=['#3F51B5']
        )
        fig_loc.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig_loc, use_container_width=True)
    
    # Simple table of follow-back opportunities
    st.write("### 🌟 Follow-Back Opportunities")
    
    # Get active users who follow you but you don't follow back
    follow_back_opportunities = [row for row in connections_data 
                                if row['following'] == 'No' and row['follower'] == 'Yes']
    
    # Sort by repository count to show most active first
    if follow_back_opportunities:
        top_opportunities = sorted(follow_back_opportunities, 
                                  key=lambda x: int(x.get('public_repos', 0)), 
                                  reverse=True)[:5]  # Top 5
        
        if top_opportunities:
            opportunity_data = [{
                "Username": row.get('username', 'Unknown'),
                "Public Repos": row.get('public_repos', '0'),
                "Location": row.get('location', 'Unknown')
            } for row in top_opportunities]
            
            st.table(pd.DataFrame(opportunity_data))
    
    # Export button
    st.download_button(
        label="Download Network Summary",
        data=pd.DataFrame({
            "Metric": ["Network Size", "Following", "Followers", "Mutual", "Influence Ratio"],
            "Value": [network_size, following_count, followers_count, mutual_followers, f"{influence_ratio:.2f}"]
        }).to_csv(index=False),
        file_name="github_network_summary.csv",
        mime="text/csv"
    )

def show_history_tab():
    """Display historical analysis data"""
    st.write("### Analysis History")
    
    # Get list of analyzed users with timestamps
    users = get_analyzed_users()
    
    if not users:
        st.info("No analysis history available.")
        return
    
    # Create a dataframe for display
    history_df = pd.DataFrame(users, columns=["Username", "Last Updated"])
    # Format the timestamp
    history_df["Last Updated"] = pd.to_datetime(history_df["Last Updated"]).dt.strftime("%Y-%m-%d %H:%M:%S")
    
    st.dataframe(history_df, use_container_width=True)
    
    # Allow comparison between analyses
    if len(users) >= 2:
        st.write("### Compare Network Changes")
        
        col1, col2 = st.columns(2)
        with col1:
            user1 = st.selectbox("Select first user", [u[0] for u in users], key="user1")
        with col2:
            user2 = st.selectbox("Select second user", [u[0] for u in users], key="user2", index=1 if len(users) > 1 else 0)
        
        if st.button("Compare Networks") and user1 != user2:
            # Get connections for both users
            connections1 = get_user_connections(user1)
            connections2 = get_user_connections(user2)
            
            # Calculate metrics
            following1 = sum(1 for row in connections1 if row['following'] == 'Yes')
            followers1 = sum(1 for row in connections1 if row['follower'] == 'Yes')
            mutual1 = sum(1 for row in connections1 if row['following'] == 'Yes' and row['follower'] == 'Yes')
            
            following2 = sum(1 for row in connections2 if row['following'] == 'Yes')
            followers2 = sum(1 for row in connections2 if row['follower'] == 'Yes')
            mutual2 = sum(1 for row in connections2 if row['following'] == 'Yes' and row['follower'] == 'Yes')
            
            # Display comparison
            comparison_data = {
                "Metric": ["Following", "Followers", "Mutual Connections", "Network Size"],
                user1: [following1, followers1, mutual1, len(connections1)],
                user2: [following2, followers2, mutual2, len(connections2)],
                "Difference": [
                    following2 - following1,
                    followers2 - followers1,
                    mutual2 - mutual1,
                    len(connections2) - len(connections1)
                ]
            }
            
            comparison_df = pd.DataFrame(comparison_data)
            st.table(comparison_df)
            
            # Visualization of differences
            fig_comp = plt.figure(figsize=(10, 6))
            x = ["Following", "Followers", "Mutual", "Network Size"]
            width = 0.35
            
            plt.bar([i - width/2 for i in range(len(x))], 
                    [following1, followers1, mutual1, len(connections1)], 
                    width, label=user1)
            plt.bar([i + width/2 for i in range(len(x))], 
                    [following2, followers2, mutual2, len(connections2)], 
                    width, label=user2)
            
            plt.xlabel('Metrics')
            plt.ylabel('Count')
            plt.title('Network Comparison')
            plt.xticks(range(len(x)), x)
            plt.legend()
            
            st.pyplot(fig_comp)

# Streamlit App
st.set_page_config(layout="wide", page_title="GitHub Followers Analyzer", page_icon="📊")
st.title("GitHub Followers Analyzer")

# Initialize database if it doesn't exist
initialize_database()

# Sidebar controls
with st.sidebar:
    st.header("Load Existing Data")
    users = get_analyzed_users()
    
    if users:
        selected_user = st.selectbox(
            "Select a previously analyzed profile:",
            options=[user[0] for user in users],
            key="existing_data"
        )
        if st.button("Load Selected Profile"):
            st.session_state.current_user = selected_user
    else:
        st.info("No analyzed profiles found. Use the form below to analyze a new profile.")

    st.markdown("---")
    
    st.header("Analyze New Profile")
    username = st.text_input("Enter GitHub Username:")
    token = st.text_input("Enter GitHub Token (optional):", type="password", 
                          help="Using a token allows for higher API rate limits")
    
    if st.button("Fetch Data"):
        if username:
            with st.spinner('Fetching data from GitHub...'):
                data = get_github_data(username, token)
                if data:
                    success = save_to_database(data, username, token)
                    if success:
                        st.success(f"Data saved for {username}")
                        st.session_state.current_user = username
                else:
                    st.error("Failed to fetch data from GitHub API. Try using a token to get more requests.")
        else:
            st.warning("Please enter a username.")

    # Add color code legend to sidebar
    st.markdown("---")
    st.write("### Color Legend")
    st.markdown("""
    <div style="display: flex; flex-direction: column; gap: 10px;">
        <div style="display: flex; align-items: center;">
            <div style="width: 20px; height: 20px; background-color: #FFCCCC; margin-right: 10px;"></div>
            <span>You follow them, they don't follow back</span>
        </div>
        <div style="display: flex; align-items: center;">
            <div style="width: 20px; height: 20px; background-color: #CCFFCC; margin-right: 10px;"></div>
            <span>Mutual followers</span>
        </div>
        <div style="display: flex; align-items: center;">
            <div style="width: 20px; height: 20px; background-color: #FFFFFF; border: 1px solid #ddd; margin-right: 10px;"></div>
            <span>They follow you, you don't follow back</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

# Main content area with tabs
if 'current_user' in st.session_state:
    current_username = st.session_state.current_user
    connections_data = get_user_connections(current_username)
    
    st.write(f"### Analysis Results for {current_username}")
    
    tab1, tab2, tab3, tab4 = st.tabs(["Overview", "Not Following Back", "Visualizations", "History"])
    
    with tab1:
        show_overview_tab(connections_data, current_username)
    
    with tab2:
        show_not_following_back_tab(connections_data)
    
    with tab3:
        show_visualizations_tab(connections_data)
    
    with tab4:
        show_history_tab()