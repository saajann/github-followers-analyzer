import requests
import csv

def get_github_data(username):
    def fetch_all_pages(url):
        results = []
        while url:
            print(f"Fetching URL: {url}")
            response = requests.get(url)
            if response.status_code != 200:
                print(f"Failed to fetch data: {response.status_code}")
                return None
            results.extend(response.json())
            url = response.links.get('next', {}).get('url')
        return results

    base_url = f"https://api.github.com/users/{username}"
    
    followers_url = f"{base_url}/followers"
    following_url = f"{base_url}/following"
    
    print(f"Fetching followers from: {followers_url}")
    followers = fetch_all_pages(followers_url)
    print(f"Fetching following from: {following_url}")
    following = fetch_all_pages(following_url)
    
    if followers is not None and following is not None:
        followers_list = [follower['login'] for follower in followers]
        following_list = [followed['login'] for followed in following]
        
        return {
            'followers': followers_list,
            'following': following_list
        }
    else:
        return {
            'error': 'Failed to fetch data from GitHub API'
        }

def save_to_csv(data):
    with open("data/github_data.csv", mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['username', 'following', 'follower', 'link'])
        
        all_users = set(data['followers']) | set(data['following'])
        
        for user in all_users:
            following = 'Yes' if user in data['following'] else 'No'
            follower = 'Yes' if user in data['followers'] else 'No'
            writer.writerow([user, following, follower, f"https://github.com/{user}"])

if __name__ == "__main__":
    username = input("Enter GitHub username: ")
    data = get_github_data(username)
    if 'error' not in data:
        save_to_csv(data)
        print(f"Data saved to github_data.csv")
    else:
        print(data['error'])
