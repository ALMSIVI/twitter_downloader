import json
import requests
import shutil

from pathlib import Path


with open('info.json') as f:
    info = json.load(f)

username = info['username']
bearer_token = info['bearer_token']
out_dir = info['out']

def create_url(id):
    params = {
        'expansions': 'attachments.media_keys',
        'media.fields': 'url'
    }
    # You can adjust ids to include a single Tweets.
    # Or you can add to up to 100 comma-separated IDs
    url = f'https://api.twitter.com/2/users/{id}/liked_tweets'
    return url, params


def bearer_oauth(r):
    r.headers['Authorization'] = f'Bearer {bearer_token}'
    r.headers['User-Agent'] = 'v2LikedTweetsPython'
    return r


def verify_resp(resp: requests.Response):
    if resp.status_code != 200:
        raise Exception(f'Request returned an error: {resp.status_code} {resp.text}')


def get_user_id(username):
    resp = requests.get(f'https://api.twitter.com/2/users/by/username/{username}', auth=bearer_oauth)
    verify_resp(resp)
    data = resp.json()
    return data['data']['id']
    

def get_likes(url, params):
    resp = requests.get(url, auth=bearer_oauth, params=params)
    verify_resp(resp)
    data = resp.json()

    out_path = Path(out_dir)

    while data['meta']['result_count'] > 0:
        # data['data'] contains the tweets and media keys.
        # data['includes'] contains the urls of medias.
        # Establish a correspondence of tweets and media urls.

        # Dictionary between keys and urls
        media_dict: dict[str, str] = {}
        for media in data['includes']['media']:
            if media['type'] == 'photo':
                media_dict[media['media_key']] = media['url']
            else:
                # Currently Twitter API v2 doesn't provide video download links. A hack will be used.
                # https://stackoverflow.com/questions/32145166
                pass



        for like in data['data']:
            tweet_path: Path = out_path / like['id']
            tweet_path.mkdir(exist_ok=True)

            text_path: Path = tweet_path / 'text.txt'
            with text_path.open('wt') as f:
                f.write(like['text'])
            
            if 'attachments' in like:
                for media_key in like['attachments']['media_keys']:
                    if media_key in media_dict:
                        url = media_dict[media_key]
                        extension = url[url.rfind('.'):]
                        resp = requests.get(url, stream=True)
                        verify_resp(resp)
                        resp.raw.decode_content = True
                        image_path = tweet_path / (media_key + extension)
                        with image_path.open('wb') as f:
                            shutil.copyfileobj(resp.raw, f)
                    # TODO: handle video above

        if 'next_token' in data['meta']:
            resp = requests.get(url, auth=bearer_oauth, params=params | {'pagination_token': data['meta']['next_token']})
        else:
            break


def main():
    user_id = get_user_id(username)
    url, params = create_url(user_id)
    get_likes(url, params)


if __name__ == '__main__':
    main()