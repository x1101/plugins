# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import re
import shutil
import sys
import tempfile
import unittest

from nikola import nikola

PLUGIN_PATH = os.path.abspath(os.path.join('v6', 'tags'))
sys.path.append(PLUGIN_PATH)

try:
    from freezegun import freeze_time
    _freeze_time = True
except ImportError:
    _freeze_time = False
    freeze_time = lambda x: lambda y: y

from tags import (
    _AutoTag, add_tags, list_tags, merge_tags, remove_tags, search_tags,
    sort_tags
)
from nikola.utils import _reload, LOGGER
import logbook
DEMO_TAGS = ['python', 'demo', 'nikola', 'blog']


def setUpModule():
    LOGGER.notice('--- TESTS FOR tags')
    LOGGER.level = logbook.WARNING


def tearDownModule():
    sys.stdout.write('\n')
    LOGGER.level = logbook.NOTICE
    LOGGER.notice('--- END OF TESTS FOR tags')


class TestCommandTagsBase(unittest.TestCase):

    def _add_test_post(self, title, tags):
        self._run_command(['new_post', '-t', title, '--tags', ','.join(tags)])

    def _create_temp_dir_and_cd(self):
        self._testdir = tempfile.mkdtemp()
        self._old_dir = os.getcwd()
        os.chdir(self._testdir)

    def _force_scan(self):
        self._site._scanned = False
        self._site.scan_posts(True)

    def _init_site(self):
        from nikola.plugins.command.init import CommandInit

        command_init = CommandInit()
        command_init.execute(options={'demo': True, 'quiet': True}, args=['demo'])

        sys.path.insert(0, '')
        os.chdir('demo')
        import conf
        _reload(conf)
        sys.path.pop(0)

        self._site = nikola.Nikola(**conf.__dict__)
        self._site.init_plugins()

    def _parse_new_tags(self, source):
        """ Returns the new tags for a post, given it's source path. """
        self._force_scan()
        posts = [
            post for post in self._site.timeline
            if post.source_path == source
        ]
        return posts[0].tags

    def _remove_temp_dir(self):
        os.chdir(self._old_dir)
        shutil.rmtree(self._testdir)

    def _run_command(self, args=[]):
        from nikola.__main__ import main
        return main(args)

    def _scan_posts(self):
        self._site.scan_posts()


class TestCommandTagsHelpers(TestCommandTagsBase):
    """ Test all the helper functions used in the plugin.

    Note: None of the tests call the actual Nikola command CommandTags.

    """

    def setUp(self):
        """ Create a demo site, for testing. """

        self._create_temp_dir_and_cd()
        self._init_site()
        # Scan for posts, since the helpers don't do it.
        self._scan_posts()

    def tearDown(self):
        """ Restore world order. """
        self._remove_temp_dir()

    # ### `TestCommandTagsHelpers` protocol ###################################

    def test_add(self):
        posts = [os.path.join('posts', post) for post in os.listdir('posts')]
        tags = 'test_nikola'

        new_tags = add_tags(self._site, tags, posts)
        new_parsed_tags = self._parse_new_tags(posts[0])

        self.assertTrue('test_nikola' in new_tags[0])
        self.assertEquals(set(new_tags[0]), set(new_parsed_tags))

    def test_add_dry_run(self):
        posts = [os.path.join('posts', post) for post in os.listdir('posts')]
        tags = 'test_nikola'

        new_tags = add_tags(self._site, tags, posts, dry_run=True)
        new_parsed_tags = self._parse_new_tags(posts[0])

        self.assertTrue('test_nikola' in new_tags[0])
        self.assertEquals(set(new_parsed_tags), set(DEMO_TAGS))

    def test_auto_tag_basic(self):
        post = os.path.join('posts', os.listdir('posts')[0])
        tagger = _AutoTag(self._site, use_nltk=False)

        # regexp to check for invalid characters in tags allow only
        # A-Za-z and hyphens.  regexp modified to make sure the whole
        # tag matches, the requirement.
        tag_pattern = re.compile('^' + _AutoTag.WORDS + '$')

        # simple tagging test.
        tags = tagger.tag(post)
        tags = [tag for tag in tags if tag_pattern.search(tag)]
        self.assertEquals(len(tags), 5)

    def test_auto_tag_nltk(self):
        post = os.path.join('posts', os.listdir('posts')[0])
        tagger = _AutoTag(self._site)

        # regexp to check for invalid characters in tags allow only
        # A-Za-z and hyphens.  regexp modified to make sure the whole
        # tag matches, the requirement.
        tag_pattern = re.compile('^' + _AutoTag.WORDS + '$')

        # tagging with nltk.
        nltk_tags = tagger.tag(post)
        tags = [tag for tag in nltk_tags if tag_pattern.search(tag)]
        self.assertEquals(len(tags), 5)

    def test_list(self):
        self.assertEquals(sorted(DEMO_TAGS), list_tags(self._site))

    def test_list_count_sorted(self):
        self._add_test_post(title='2', tags=['python'])
        self._force_scan()
        tags = list_tags(self._site, 'count')
        self.assertEquals('python', tags[0])

    def test_list_draft(self):
        self._add_test_post(title='2', tags=['python', 'draft'])
        self._force_scan()
        tags = list_tags(self._site)
        self.assertIn('draft', tags)

    def test_list_draft_post_tags(self):
        self._add_test_post(title='2', tags=['ruby', 'draft'])
        self._force_scan()
        tags = list_tags(self._site)
        self.assertIn('ruby', tags)

    @unittest.skipIf(not _freeze_time, 'freezegun package not installed.')
    def test_list_scheduled_post_tags(self):
        with freeze_time("2012-01-14"):
            self._force_scan()
            tags = list_tags(self._site)
            self.assertIn('python', tags)

    def test_merge(self):
        posts = [os.path.join('posts', post) for post in os.listdir('posts')]
        tags = 'nikola, python'

        new_tags = merge_tags(self._site, tags, posts)
        new_parsed_tags = self._parse_new_tags(posts[0])

        self.assertFalse('nikola' in new_tags)
        self.assertEquals(set(new_tags[0]), set(new_parsed_tags))

    def test_merge_dry_run(self):
        posts = [os.path.join('posts', post) for post in os.listdir('posts')]
        tags = 'nikola, python'

        new_tags = merge_tags(self._site, tags, posts, dry_run=True)
        new_parsed_tags = self._parse_new_tags(posts[0])

        self.assertFalse('nikola' in new_tags[0])
        self.assertEquals(set(DEMO_TAGS), set(new_parsed_tags))

    def test_remove(self):
        posts = [os.path.join('posts', post) for post in os.listdir('posts')]
        tags = 'nikola'

        new_tags = remove_tags(self._site, tags, posts)
        new_parsed_tags = self._parse_new_tags(posts[0])

        self.assertFalse('nikola' in new_tags)
        self.assertEquals(set(new_tags[0]), set(new_parsed_tags))

    def test_remove_draft(self):
        self._add_test_post(title='2', tags=['draft'])
        self._force_scan()
        posts = [os.path.join('posts', post) for post in os.listdir('posts')]

        remove_tags(self._site, 'draft', posts)
        self._force_scan()

        tags = list_tags(self._site, 'count')
        self.assertNotIn('draft', tags)

    def test_remove_invalid(self):
        posts = [os.path.join('posts', post) for post in os.listdir('posts')]
        tags = 'wordpress'

        new_tags = remove_tags(self._site, tags, posts)
        new_parsed_tags = self._parse_new_tags(posts[0])

        self.assertEquals(set(new_tags[0]), set(new_parsed_tags))

    def test_remove_dry_run(self):
        posts = [os.path.join('posts', post) for post in os.listdir('posts')]
        tags = 'nikola'

        new_tags = remove_tags(self._site, tags, posts, dry_run=True)
        new_parsed_tags = self._parse_new_tags(posts[0])

        self.assertFalse('nikola' in new_tags[0])
        self.assertEquals(set(new_parsed_tags), set(DEMO_TAGS))

    def test_search(self):
        search_terms = {
            'l': ['blog', 'nikola'],
            '.*': sorted(DEMO_TAGS),
            '^ni.*': ['nikola']
        }
        for term in search_terms:
            tags = search_tags(self._site, term)
            self.assertEquals(tags, search_terms[term])

    def test_sort(self):
        posts = [os.path.join('posts', post) for post in os.listdir('posts')]

        new_tags = sort_tags(self._site, posts)
        new_parsed_tags = self._parse_new_tags(posts[0])

        self.assertEquals(sorted(DEMO_TAGS), new_parsed_tags)
        self.assertEquals(sorted(DEMO_TAGS), new_tags[0])

    def test_sort_dry_run(self):
        posts = [os.path.join('posts', post) for post in os.listdir('posts')]

        old_parsed_tags = self._parse_new_tags(posts[0])
        new_tags = sort_tags(self._site, posts, dry_run=True)
        new_parsed_tags = self._parse_new_tags(posts[0])

        self.assertEquals(old_parsed_tags, new_parsed_tags)
        self.assertEquals(sorted(DEMO_TAGS), new_tags[0])


class TestCommandTags(TestCommandTagsBase):
    """ Tests that directly call the Nikola command CommandTags. """

    def setUp(self):
        """ Create a demo site, for testing. """

        self._create_temp_dir_and_cd()
        self._init_site()
        # Don't scan for posts.  The command should do it.
        self._copy_plugin_to_site()

    def tearDown(self):
        """ Restore world order. """
        self._remove_temp_dir()

    # ### `TestCommandTags` protocol ###########################################

    def test_list_count_sorted(self):
        self._add_test_post(title='2', tags=['python'])
        tags = self._run_shell_command(['nikola', 'tags', '-l', '-s', 'count'])
        self.assertTrue('python' in tags)
        self.assertEquals('python', tags.split()[1])

    @unittest.skipIf(sys.version_info[0] == 3, 'Py2.7 specific bug.')
    def test_merge_unicode_tags(self):
        # Regression test for #63
        exit_code = self._run_command(['tags', '--merge', u'paran\xe3,parana'.encode('utf8'), 'posts/1.rst'])
        self.assertFalse(exit_code)

    # ### `Private` protocol ###########################################

    def _copy_plugin_to_site(self):
        if not os.path.exists('plugins'):
            os.makedirs('plugins')
        shutil.copytree(PLUGIN_PATH, os.path.join('plugins', 'tags'))

    def _run_shell_command(self, args):
        import subprocess
        try:
            output = subprocess.check_output(args)
        except (OSError, subprocess.CalledProcessError):
            return ''
        else:
            return output.decode('utf-8')


if __name__ == '__main__':
    unittest.main()
