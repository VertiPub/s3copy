s3copy
======

**s3copy** - multi-threaded, fault-tolerant, bucket-to-bucket copy for
s3

Usage
-----

Simple example:

::

    s3copy s3://source/path s3://dest/path

All the files in the source bucket contained in path are copied to the
destination bucket at the specified path (paths may be omitted for
either source or destination).

Some common arguments:

::

    s3copy s3://source/path s3://dest/path -n

The above example is a dry-run (-n), so it does no copying but indicates
what copying it would do.

::

    s3copy s3://source/path s3://dest/path -t 20 -l DEBUG -L log.txt

The above example uses 20 threads, prints log messages down to the DEBUG
level, and appends its log to a file named log.txt.

::

    s3copy --help

The above example prints help.

Source and Destination Paths
----------------------------

Paths behave similarly to the unix "cp -r" command. Suppose for example
that the source bucket contains the following files:

::

      folder-001/test-001
      folder-001/test-002

and suppose in each case below that the destination folder is initially
empty. Then these commands have these results:

+------------------------------------------+-------------------------------------------------+
| Command                                  | Result files in dest                            |
+==========================================+=================================================+
| s3copy s3://source s3://dest             | folder-001/test-001 folder-001/test-002         |
+------------------------------------------+-------------------------------------------------+
| s3copy s3://source s3://dest/foo         | foo/folder-001/test-001 foo/folder-001/test-002 |
+------------------------------------------+-------------------------------------------------+
| s3copy s3://source/folder-001 s3://dest  | folder-001/test-001 folder-001/test-002         |
+------------------------------------------+-------------------------------------------------+
|s3copy s3://source/folder-001/* s3://dest | test-001 test-002                               |
+------------------------------------------+-------------------------------------------------+

Globbing support is limited to a single ``*`` at the end of a pattern.
Internal ``*`` and other pattern characters are not supported.

Restart and Sync
----------------

s3copy is fault-tolerant and restartable. If a copy run is interrupted
or fails for any reason, you can repeat the command and it will complete
the operation. It does this by checking the md5s of the individual
source and destination files. In this way, s3copy can also be used to
sync buckets. If an s3copy command succeeeds and the source bucket
subsequently changes, with the addition of new files or changes to
existing files, the same command can be run again and only the changes
will be copied. Note that additions and changes are supported but
deletions are not: if a file is deleted from the source and the command
is rerun, the corresponding file in the destination will not deleted.

Multipart File Handling
-----------------------

Amazon S3 can currently store individual files up to a limit of 5
terabytes (http://aws.amazon.com/s3/faqs/), however files above 5GB must
be stored as "multipart" files. Multipart files are created and copied
in multiple transactions, using special apis that specify a byte offset
and length.

Multipart files present special difficulties for copying:

-  S3 does not expose the md5 of the entire file, nor of its constituent
   parts. It does report the md5 of a part as it is copied. It also
   exposes an "etag" of the file, which resembles an md5 hash (discussed
   further below).
-  S3 does not permit creating a simple, non-multipart file directly
   from a portion of a multipart file. That is, when copying a portion,
   both the source and target must be multipart.

In addition, although files larger than 5GB *must* be multipart, files
smaller than 5GB *may* be. For example, it is faster and more reliable
to create a 5GB file (the maximum non-multipart file) in 80 chunks of
64MB each, rather than as a single 5GB file. For these reasons, s3copy
handles multipart files bigger and smaller than 5GB.

Multipart files are copied in parts. The default part size is 64MB, but
this can be controlled by the ``-p`` option. For validation and
restartability, the part files are copied in three steps:

1. Each part is copied to a multipart file with a single part in a temp
   area on the destination bucket. As noted above, one can not create a
   single part file directly from a part of a multipart file. As this
   copy occurs, s3copy keeps the md5 of the part in memory (since, as
   noted above, S3 does not expose the md5 of a multipart file, even if
   it has only one part).
2. Each part is then copied to a temporary simple file. S3 does expose
   the md5 of this file. s3copy validates that the md5 of the file
   matches the md5 of the portion which S3 reported in step 1.
3. The final target file is created as a multipart file from the
   constituent simple files.

This process means that the data bytes of a multipart file are copied
three times, whereas in principle they could have been copied only once,
as a multipart copy of the source to the target. The extra copies enable
restartability and validation, as follows:

-  Restartability: steps one and two create durable temp files which
   s3copy can observe to determine which parts of a multipart copy have
   already occurred.
-  Validation: During the multipart copy in step three, the md5s of each
   component can be revalidated against the stored md5s of the parts.

It should be noted that only step one involves data transfer between the
source and destination buckets. Steps two and three are copies from the
destination bucket to itself, and are thus inside the same S3 data
center. Data transfer inside a data center is very fast and is
(currently) free. Amazon only charges for data transfer between data
centers, and this methodology does the minimum cross-data-center
copying. The author's experience is that the restartability justifies
the longer throughput time.

By default, the temporary files are created in a directory named "temp",
named as follows. For each multipart source file, for example, named
"source/path/to/file-to-split", we use a directory named
"dest/temp/path/to/file-to-split//parts". The versionid is the first 7
characters of the "etag" of the source multi-part file. Inside that
directory, the temporary 1-part-multipart files are named "temp-00001",
"temp-00002", etc., and the single-part files are named "part-00001",
"part-00002", etc. In some situations, such as subsequent transfer to
hdfs, retaining the part files may be useful. By default, all these
files are retained.

Security and Access
-------------------

If needed, you can supply two credentials sets to s3copy: one for
accessing the source bucket and copying to the destination and one for
listing the destination bucket. This is useful for cross-account copying
when you are given a set of credentials to access the source, but those
credentials can not list the destination. Supply a second set of
credentials by using the ``-d`` option.

You can grant access to files created on the destination by specifying
the ``--acl-grant`` option. The grantee must be an email address.

Testing Notes
------------

To run the tests, edit the s3copy_test_settings.py for your local environment, then run this command:

    python test_s3copy

On-line Help
------------

This is the current built-in on-line help:

::

    s3copy --help

    usage: s3copy [-h] [-n] [-f FILE [FILE ...]] [-p PREFIX [PREFIX ...]]
                  [-F FILES] [-P PREFIXES] [-a AWS_ACCESS_KEY] [-k AWS_SECRET_KEY]
                  [-c S3CFG_FILE] [-d DEST_S3CFG_FILE] [--acl-grant ACL_GRANT]
                  [-t NUM_THREADS] [-l LOG_LEVEL] [-L LOG_DEST]
                  source_bucket [dest_bucket]

    Multithreaded multipart copier for Amazon S3

    positional arguments:
      source_bucket         source bucket/path
      dest_bucket           destination bucket/path

    optional arguments:
      -h, --help            show this help message and exit
      -n, --dry-run         do no work but report what work would be done
      -f FILE [FILE ...], --file FILE [FILE ...]
                            source file[s] to copy
      -p PREFIX [PREFIX ...], --prefix PREFIX [PREFIX ...]
                            source prefix[es] to copy
      -F FILES, --files FILES
                            file containing a list of files to copy
      -P PREFIXES, --prefixes PREFIXES
                            file containing a list of prefixes to copy
      -a AWS_ACCESS_KEY     AWS Access Key
      -k AWS_SECRET_KEY     AWS Secret Key
      -c S3CFG_FILE, --config_file S3CFG_FILE
                            s3cmd-format config file
      -d DEST_S3CFG_FILE, --dest-config DEST_S3CFG_FILE
                            s3cmd-format config file for destination bucket only
      --acl-grant ACL_GRANT
                            acl to grant as PERMISSION:EMAIL
      -t NUM_THREADS        number of threads (default: 40)
      -l LOG_LEVEL          logging level
      -L LOG_DEST           logging file (appended)

