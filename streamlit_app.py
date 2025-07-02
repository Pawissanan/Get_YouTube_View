import streamlit as st
import pandas as pd
import re
from datetime import datetime
import googleapiclient.discovery as youtube

def fetch_youtube_data(api_key, channel_id, start_month_year, end_month_year, keyword, hashtag_keywords, include_description):
    try:
        youtube_api = youtube.build('youtube', 'v3', developerKey=api_key)

        start_month = int(start_month_year[:2])
        start_year = int(start_month_year[2:])
        end_month = int(end_month_year[:2])
        end_year = int(end_month_year[2:])

        uploads_playlist_response = youtube_api.channels().list(
            part='contentDetails,snippet', id=channel_id).execute()

        if 'items' not in uploads_playlist_response or len(uploads_playlist_response['items']) == 0:
            st.warning(f"No items found for channel ID: {channel_id}")
            return None

        uploads_playlist_id = uploads_playlist_response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
        channel_name = uploads_playlist_response['items'][0]['snippet']['title']

        video_data = {
            'Channel Name': [],
            'Video Title': [],
            'Description': [],  # Only hashtags
            'Published Date': [],
            'View Count': []
        }

        next_page_token = ''
        while next_page_token is not None:
            playlist_items_response = youtube_api.playlistItems().list(
                part='contentDetails', playlistId=uploads_playlist_id,
                maxResults=50, pageToken=next_page_token).execute()
            video_ids = [item['contentDetails']['videoId'] for item in playlist_items_response['items']]

            for video_id in video_ids:
                video_response = youtube_api.videos().list(part='statistics,snippet', id=video_id).execute()
                snippet = video_response['items'][0]['snippet']
                statistics = video_response['items'][0]['statistics']

                video_title = snippet.get('title', '')
                view_count = int(statistics.get('viewCount', 0))
                published_date_str = snippet.get('publishedAt', '')
                published_date = datetime.fromisoformat(published_date_str[:-1])

                # ✅ Keyword filter (if any)
                if keyword:
                    description_preview = snippet.get('description', '')
                        if keyword not in video_title.lower() and keyword not in description_preview.lower():
                            continue

                # ✅ Date filter
                if start_year <= published_date.year <= end_year and start_month <= published_date.month <= end_month:

                    # ✅ Conditionally fetch and process description and hashtags
                    if include_description:
                        description = snippet.get('description', '')
                        hashtags = re.findall(r'#\S+', description)
                        hashtags_lower = [h.lower() for h in hashtags]

                   # ✅ Hashtag filter
                   if hashtag_keywords:
                      if not any(h in hashtags_lower for h in hashtag_keywords):
                          continue

                   description_output = ', '.join(hashtags)
                 else:
                   description_output = ''

                # ✅ Append video data
                video_data['Channel Name'].append(channel_name)
                video_data['Video Title'].append(video_title)
                video_data['View Count'].append(view_count)
                video_data['Published Date'].append(published_date.date())
                video_data['Description'].append(description_output)

            next_page_token = playlist_items_response.get('nextPageToken')

        return pd.DataFrame(video_data)

    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        return None

# Streamlit UI
st.title("YouTube Channel View Extractor")
st.markdown("""report bug : `pawissanan.denphatcharangkul@initiative.com`""")

api_key = st.text_input("🔑 Enter your YouTube API Key:", type="password")

channel_ids_input = st.text_area("📺 Enter YouTube Channel IDs (one per line):")
channel_ids = [c.strip() for c in channel_ids_input.splitlines() if c.strip()]
with st.expander("❓ How to find a YouTube Channel ID"):
    st.markdown("""
    1. Go to the target channel’s **YouTube page** in your browser  
    2. Press `Ctrl + U` to **view the page source**  
    3. Press `Ctrl + F` to search and enter `channel_id=`  
    4. Copy the text **after** `channel_id=` — it will look like this:  
       `UCxxxxxxxxxxxxxxxxxxxxxx`  
       
    ✅ Example: `UCNpSm55KmljJvQ3Sr20bmTQ`
    """)
    
col1, col2 = st.columns(2)
with col1:
    start_month_year = st.text_input("Start Month & Year (MMYYYY)", value="")
with col2:
    end_month_year = st.text_input("End Month & Year (MMYYYY)", value="")
include_description = st.checkbox("Include video description and hashtags (uses more API quota)", value=True)
keyword = st.text_input("🔍 Filter by keyword in title and description (optional):").lower()
hashtag_filter = st.text_input("🔎 Filter by hashtag(s), separated by commas (e.g. #AI, #tech) (optional)").lower()
# Convert to a list of lowercase hashtags
hashtag_keywords = [tag.strip() for tag in hashtag_filter.split(',') if tag.strip()]

if st.button("Run Analysis"):
    st.write("Keyword:", keyword)
    st.write("Hashtag:", hashtag_filter)
    if not api_key or not channel_ids:
        st.warning("Please enter both API key and at least one channel ID.")
    else:
        df_list = []
        with st.spinner("Fetching data from YouTube..."):
            for cid in channel_ids:
                df = fetch_youtube_data(api_key, cid, start_month_year, end_month_year)
                if df is not None and not df.empty:
                    df_list.append(df)

        if df_list:
            result_df = pd.concat(df_list, ignore_index=True)
            st.success("✅ Data fetched successfully!")
            st.dataframe(result_df)

            # Excel download
            file_name = f"youtube_data_{start_month_year}_{end_month_year}.xlsx"
            result_df.to_excel(file_name, index=False)

            with open(file_name, "rb") as f:
                st.download_button(
                    label="📥 Download Excel File",
                    data=f,
                    file_name=file_name,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        else:
            st.warning("No data found for the selected period.")
