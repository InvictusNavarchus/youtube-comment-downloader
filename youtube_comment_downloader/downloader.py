"""YouTube comment downloader implementation."""

from __future__ import print_function

import json
import re
import time
from typing import Dict, Any, Generator, Optional, List, Union

import dateparser
import requests

from .constants import (
    YOUTUBE_VIDEO_URL, YOUTUBE_CONSENT_URL, USER_AGENT, 
    SORT_BY_POPULAR, SORT_BY_RECENT, YT_CFG_RE, 
    YT_INITIAL_DATA_RE, YT_HIDDEN_INPUT_RE
)
from .exceptions import (
    CommentDownloadError, SortingError, 
    CommentsDisabledError, YouTubeApiError
)
from .utils import regex_search, search_dict


class YoutubeCommentDownloader:
    """
    A class for downloading YouTube comments without using the YouTube API.
    """

    def __init__(self):
        """Initialize the YouTube comment downloader with a session."""
        self.session = requests.Session()
        self.session.headers['User-Agent'] = USER_AGENT
        self.session.cookies.set('CONSENT', 'YES+cb', domain='.youtube.com')

    def ajax_request(self, endpoint: Dict[str, Any], ytcfg: Dict[str, Any], 
                    retries: int = 5, sleep: int = 20, timeout: int = 60) -> Optional[Dict[str, Any]]:
        """
        Make an AJAX request to the YouTube API.

        Args:
            endpoint: Endpoint data
            ytcfg: YouTube configuration data
            retries: Number of retries
            sleep: Sleep time between retries in seconds
            timeout: Request timeout in seconds

        Returns:
            Response JSON or None if failed
        """
        url = 'https://www.youtube.com' + endpoint['commandMetadata']['webCommandMetadata']['apiUrl']

        data = {
            'context': ytcfg['INNERTUBE_CONTEXT'],
            'continuation': endpoint['continuationCommand']['token']
        }

        for _ in range(retries):
            try:
                response = self.session.post(
                    url, 
                    params={'key': ytcfg['INNERTUBE_API_KEY']}, 
                    json=data, 
                    timeout=timeout
                )
                if response.status_code == 200:
                    return response.json()
                if response.status_code in [403, 413]:
                    return {}
            except requests.exceptions.Timeout:
                pass
            time.sleep(sleep)
        return None

    def get_comments(self, youtube_id: str, sort_by: int = SORT_BY_RECENT, 
                    language: Optional[str] = None, sleep: float = 0.1) -> Generator[Dict[str, Any], None, None]:
        """
        Get comments for a YouTube video ID.

        Args:
            youtube_id: YouTube video ID
            sort_by: Sort method (SORT_BY_POPULAR or SORT_BY_RECENT)
            language: Language for YouTube generated text
            sleep: Sleep time between requests in seconds

        Yields:
            Comment data dictionaries
        """
        url = YOUTUBE_VIDEO_URL.format(youtube_id=youtube_id)
        yield from self.get_comments_from_url(url, sort_by, language, sleep)

    def get_comments_from_url(self, youtube_url: str, sort_by: int = SORT_BY_RECENT, 
                            language: Optional[str] = None, sleep: float = 0.1) -> Generator[Dict[str, Any], None, None]:
        """
        Get comments from a YouTube URL.

        Args:
            youtube_url: Full YouTube video URL
            sort_by: Sort method (SORT_BY_POPULAR or SORT_BY_RECENT)
            language: Language for YouTube generated text
            sleep: Sleep time between requests in seconds

        Yields:
            Comment data dictionaries

        Raises:
            CommentDownloadError: If comments cannot be downloaded
            SortingError: If sorting method cannot be applied
            CommentsDisabledError: If comments are disabled for the video
            YouTubeApiError: If YouTube API returns an error
        """
        # Fetch the page
        response = self.session.get(youtube_url)

        # Handle consent page if needed
        if 'consent' in str(response.url):
            params = dict(re.findall(YT_HIDDEN_INPUT_RE, response.text))
            params.update({'continue': youtube_url, 'set_eom': False, 'set_ytc': True, 'set_apyt': True})
            response = self.session.post(YOUTUBE_CONSENT_URL, params=params)

        # Extract configuration data
        html = response.text
        ytcfg = json.loads(regex_search(html, YT_CFG_RE, default='{}'))
        if not ytcfg:
            raise CommentDownloadError("Unable to extract YouTube configuration")
            
        if language:
            ytcfg['INNERTUBE_CONTEXT']['client']['hl'] = language

        # Extract initial data
        data = json.loads(regex_search(html, YT_INITIAL_DATA_RE, default='{}'))

        # Check if comments are available
        item_section = next(search_dict(data, 'itemSectionRenderer'), None)
        renderer = next(search_dict(item_section, 'continuationItemRenderer'), None) if item_section else None
        if not renderer:
            raise CommentsDisabledError("Comments may be disabled for this video")

        # Get sort menu and set up continuations
        sort_menu = next(search_dict(data, 'sortFilterSubMenuRenderer'), {}).get('subMenuItems', [])
        if not sort_menu:
            # Try to find continuations in section list for community posts
            section_list = next(search_dict(data, 'sectionListRenderer'), {})
            continuations = list(search_dict(section_list, 'continuationEndpoint'))
            if continuations:
                data = self.ajax_request(continuations[0], ytcfg) or {}
                sort_menu = next(search_dict(data, 'sortFilterSubMenuRenderer'), {}).get('subMenuItems', [])
        
        if not sort_menu or sort_by >= len(sort_menu):
            raise SortingError(f"Failed to set sorting method: {sort_by}")
            
        continuations = [sort_menu[sort_by]['serviceEndpoint']]

        # Process continuations and yield comments
        while continuations:
            continuation = continuations.pop()
            response = self.ajax_request(continuation, ytcfg)

            if not response:
                break

            error = next(search_dict(response, 'externalErrorMessage'), None)
            if error:
                raise YouTubeApiError(f"Error returned from YouTube API: {error}")

            # Process continuations
            actions = list(search_dict(response, 'reloadContinuationItemsCommand')) + \
                      list(search_dict(response, 'appendContinuationItemsAction'))
                      
            for action in actions:
                for item in action.get('continuationItems', []):
                    if action['targetId'] in ['comments-section',
                                              'engagement-panel-comments-section',
                                              'shorts-engagement-panel-comments-section']:
                        # Process continuations for comments and replies
                        continuations[:0] = [ep for ep in search_dict(item, 'continuationEndpoint')]
                    if action['targetId'].startswith('comment-replies-item') and 'continuationItemRenderer' in item:
                        # Process the 'Show more replies' button
                        continuations.append(next(search_dict(item, 'buttonRenderer'))['command'])

            # Process payments/memberships
            surface_payloads = search_dict(response, 'commentSurfaceEntityPayload')
            payments = {payload['key']: next(search_dict(payload, 'simpleText'), '')
                        for payload in surface_payloads if 'pdgCommentChip' in payload}
                        
            if payments:
                # Map the payload keys to the comment IDs
                view_models = [vm['commentViewModel'] for vm in search_dict(response, 'commentViewModel')]
                surface_keys = {vm['commentSurfaceKey']: vm['commentId']
                                for vm in view_models if 'commentSurfaceKey' in vm}
                payments = {surface_keys[key]: payment for key, payment in payments.items() if key in surface_keys}

            # Process toolbar states
            toolbar_payloads = search_dict(response, 'engagementToolbarStateEntityPayload')
            toolbar_states = {payload['key']: payload for payload in toolbar_payloads}
            
            # Process comments
            for comment in reversed(list(search_dict(response, 'commentEntityPayload'))):
                properties = comment['properties']
                cid = properties['commentId']
                author = comment['author']
                toolbar = comment['toolbar']
                toolbar_state = toolbar_states[properties['toolbarStateKey']]
                
                result = {
                    'cid': cid,
                    'text': properties['content']['content'],
                    'time': properties['publishedTime'],
                    'author': author['displayName'],
                    'channel': author['channelId'],
                    'votes': toolbar['likeCountNotliked'].strip() or "0",
                    'replies': toolbar['replyCount'],
                    'photo': author['avatarThumbnailUrl'],
                    'heart': toolbar_state.get('heartState', '') == 'TOOLBAR_HEART_STATE_HEARTED',
                    'reply': '.' in cid
                }

                # Add parsed timestamp if possible
                try:
                    result['time_parsed'] = dateparser.parse(result['time'].split('(')[0].strip()).timestamp()
                except AttributeError:
                    pass

                # Add payment information if available
                if cid in payments:
                    result['paid'] = payments[cid]

                yield result
                
            time.sleep(sleep)
