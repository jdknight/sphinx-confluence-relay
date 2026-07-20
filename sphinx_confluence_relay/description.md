This service provides the ability to proxy publish requests for
Confluence-generated document using
[Atlassian® Confluence® Builder][sphinxcontrib-confluencebuilder] for
[Sphinx][sphinx]. While users can publish directly with the extension, users
may wish publish at a later stage and publish with a service which manages a
Confluence API token itself.

Note that this service only supports Confluence Data Center.

## Usage

When running Sphinx, ensure [`confluence_publish`][confluence_publish] is
disabled to avoid attempts to publish with the extension. In addition,
configure [`confluence_manifest_data`][confluence_manifest_data] to
generate full manifest definition.

```
confluence_publish = False
confluence_manifest_data = True
```

After building documentation, the output folder should contain a manifest file:

```
scb-manifest.json
```

This file can be used in the publish request provided by this service. Provide
at least the space name and this manifest, the service will queue and
eventually publish queue pages/files. After queuing the publish request, it
may take a moment to publish. A user can query the status of a recently
generated request using the request identifier returned when the request
was made.

A publish request may require an instance API key to publish if the system
administrator has configured authentication.

Users looking for a simple publish setup in their environment may opt-in
to installing this package:

```
pipx install sphinx-confluence-relay
```

Which will provide a `sphinx-confluence-relay-publish` command to publish a
manifest generated from a documentation build event. For example, after
generating documentation using a command similar to:

```
sphinx-build -M confluence . _build -E -a
```

A user can publish the manifest by using the command:

```
sphinx-confluence-relay-publish http://upload.wiki.example.com/ --space-key MYSPACE --parent-page MyPublishDocs
```

Or:

```
export SPHINX_CONFLUENCE_RELAY_PUBLISH_PARENT=MyPublishDocs
export SPHINX_CONFLUENCE_RELAY_PUBLISH_SPACE=MYSPACE
export SPHINX_CONFLUENCE_RELAY_PUBLISH_URL=http://upload.wiki.example.com/

sphinx-confluence-relay-publish
```

<hr />

<small>
This project is unaffiliated with Atlassian.
    <br />
Atlassian is a registered trademark of Atlassian Pty Ltd.
    <br />
Confluence is a registered trademark of Atlassian Pty Ltd.
</small>

[confluence_manifest_data]: https://sphinxcontrib-confluencebuilder.readthedocs.io/configuration/#confval-confluence_manifest_data
[confluence_publish]: https://sphinxcontrib-confluencebuilder.readthedocs.io/configuration/#confval-confluence_publish
[sphinx]: https://www.sphinx-doc.org/
[sphinxcontrib-confluencebuilder]: https://sphinxcontrib-confluencebuilder.readthedocs.io/
