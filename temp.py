import streamlit as st
import requests
import csv
import os
import matplotlib.pyplot as plt
import seaborn as sns
import glob
from datetime import datetime
import pandas as pd
import networkx as nx
from collections import Counter
import time
from datetime import datetime, timezone

@st.cache_data(ttl=3600)
def fetch_user_details(username):
    response = requests.get(f"https://api.github.com/users/{username}")
    if response.status_code == 200:
        return response.json()
    return None

@st.cache_data(ttl=3600)
def fetch_user_repos(username):
    response = requests.get(f"https://api.github.com/users/{username}/repos")
    if response.status_code == 200:
        return response.json()
    return []

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
        # Fetch detailed information for each user
        follower_details = []
        for f in followers:
            details = fetch_user_details(f['login'])
            if details:
                follower_details.append({
                    'login': f['login'],
                    'type': details.get('type', ''),
                    'created_at': details.get('created_at', ''),
                    'public_repos': details.get('public_repos', 0),
                    'followers': details.get('followers', 0),
                    'following': details.get('following', 0),
                    'location': details.get('location', ''),
                    'company': details.get('company', ''),
                })
            time.sleep(0.1)  # Rate limiting
        
        return {
            'followers': follower_details,
            'following': [f['login'] for f in following],
            'user_details': fetch_user_details(username)
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
        writer.writerow(['username', 'following', 'follower', 'type', 'created_at', 
                        'public_repos', 'followers_count', 'following_count',
                        'location', 'company', 'link'])
        
        # Process followers
        for f in data['followers']:
            writer.writerow([
                f['login'],
                'Yes' if f['login'] in data['following'] else 'No',
                'Yes',
                f['type'],
                f['created_at'],
                f['public_repos'],
                f['followers'],
                f['following'],
                f['location'],
                f['company'],
                f"https://github.com/{f['login']}"
            ])
        
        # Process following-only users
        for username in data['following']:
            if username not in [f['login'] for f in data['followers']]:
                details = fetch_user_details(username)
                if details:
                    writer.writerow([
                        username,
                        'Yes',
                        'No',
                        details.get('type', ''),
                        details.get('created_at', ''),
                        details.get('public_repos', 0),
                        details.get('followers', 0),
                        details.get('following', 0),
                        details.get('location', ''),
                        details.get('company', ''),
                        f"https://github.com/{username}"
                    ])
                time.sleep(0.1)  # Rate limiting
    
    return filepath

def read_csv(filepath):
    return pd.read_csv(filepath)

def get_existing_csv_files():
    return glob.glob("data/github_data_*.csv")

def calculate_influence_score(row):
    # Simple influence score based on followers and public repos
    return (row['followers_count'] * 0.7 + row['public_repos'] * 0.3) / 100

def analyze_network(df):
    # Create a network graph of mutual followers
    G = nx.Graph()
    mutual_followers = df[df['follower'] == 'Yes'][df['following'] == 'Yes']
    
    for _, row in mutual_followers.iterrows():
        G.add_node(row['username'])
    
    # Add edges between nodes that have similar interests (public repos)
    for i, row1 in mutual_followers.iterrows():
        for j, row2 in mutual_followers.iterrows():
            if i < j:
                if abs(row1['public_repos'] - row2['public_repos']) < 10:
                    G.add_edge(row1['username'], row2['username'])
    
    return G

# Streamlit App
st.set_page_config(layout="wide", page_title="GitHub Network Analyzer")

st.title("GitHub Network Analyzer")
st.markdown("""
This enhanced analyzer helps you understand your GitHub network better by providing:
- Detailed follower analytics
- Network visualization
- Influence metrics
- Geographic distribution
- User categorization
""")

# Add file selector for existing CSV files
existing_files = get_existing_csv_files()
if existing_files:
    st.sidebar.write("### Load Existing Data")
    selected_file = st.sidebar.selectbox(
        "Select existing data file:",
        options=existing_files,
        format_func=lambda x: os.path.basename(x).replace('github_data_', '').replace('.csv', '')
    )

# Input for new username
st.sidebar.write("### Fetch New Data")
username = st.sidebar.text_input("Enter GitHub Username:")

if st.sidebar.button("Fetch Data"):
    if username:
        with st.spinner('Fetching data from GitHub... This might take a few minutes.'):
            data = get_github_data(username)
            if data:
                csv_file = save_to_csv(data, username)
                st.success(f"Data saved to {csv_file}")
                selected_file = csv_file
            else:
                st.error("Failed to fetch data from GitHub API")
    else:
        st.warning("Please enter a username.")

# Process and display data
if 'selected_file' in locals() and os.path.exists(selected_file):
    df = read_csv(selected_file)
    current_username = os.path.basename(selected_file).replace('github_data_', '').replace('.csv', '')
    
    # Calculate additional metrics
    df['account_age'] = pd.to_datetime(df['created_at']).apply(lambda x: (datetime.now(timezone.utc) - x).days)
    df['influence_score'] = df.apply(calculate_influence_score, axis=1)
    
    # Main metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Following", len(df[df['following'] == 'Yes']))
    with col2:
        st.metric("Total Followers", len(df[df['follower'] == 'Yes']))
    with col3:
        st.metric("Mutual Connections", len(df[df['following'] == 'Yes'][df['follower'] == 'Yes']))
    with col4:
        following_count = len(df[df['following'] == 'Yes'])
        followers_count = len(df[df['follower'] == 'Yes'])
        if following_count > 0:
            ratio = followers_count / following_count
            st.metric("Follower Ratio", f"{ratio:.2f}")
    
    # Tabs for different analyses
    tab1, tab2, tab3, tab4 = st.tabs(["Network Insights", "User Analysis", "Geographic Distribution", "Account Types"])
    
    with tab1:
        col1, col2 = st.columns(2)
        with col1:
            st.write("### Network Graph")
            G = analyze_network(df)
            fig, ax = plt.subplots(figsize=(10, 10))
            nx.draw(G, with_labels=True, node_color='lightblue', 
                   node_size=500, font_size=8, ax=ax)
            st.pyplot(fig)
        
        with col2:
            st.write("### Most Influential Followers")
            influential = df.sort_values('influence_score', ascending=False).head(10)
            st.dataframe(influential[['username', 'followers_count', 'public_repos', 'influence_score']])
    
    with tab2:
        col1, col2 = st.columns(2)
        with col1:
            st.write("### Account Age Distribution")
            fig, ax = plt.subplots()
            sns.histplot(data=df, x='account_age', bins=20, ax=ax)
            ax.set_xlabel("Account Age (days)")
            st.pyplot(fig)
        
        with col2:
            st.write("### Repository Distribution")
            fig, ax = plt.subplots()
            sns.boxplot(data=df, y='public_repos', ax=ax)
            ax.set_ylabel("Number of Public Repositories")
            st.pyplot(fig)
    
    with tab3:
        st.write("### Geographic Distribution")
        location_counts = df['location'].value_counts().head(10)
        fig, ax = plt.subplots()
        location_counts.plot(kind='bar', ax=ax)
        plt.xticks(rotation=45)
        st.pyplot(fig)
    
    with tab4:
        col1, col2 = st.columns(2)
        with col1:
            st.write("### Account Types")
            account_types = df['type'].value_counts()
            fig, ax = plt.subplots()
            plt.pie(account_types.values, labels=account_types.index, autopct='%1.1f%%')
            st.pyplot(fig)
        
        with col2:
            st.write("### Company Distribution")
            company_counts = df['company'].value_counts().head(10)
            fig, ax = plt.subplots()
            company_counts.plot(kind='bar', ax=ax)
            plt.xticks(rotation=45)
            st.pyplot(fig)
    
    # Export options
    st.sidebar.write("### Export Data")
    st.sidebar.download_button(
        label="Download Full Dataset",
        data=df.to_csv(index=False).encode('utf-8'),
        file_name=f"github_network_{current_username}.csv",
        mime="text/csv"
    )