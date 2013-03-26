import unittest
import subprocess
import re

from s3copy_test_settings import CFG0, CFG1, CFG2, TESTSRC1, TESTDST1


def runcmd(cmd_or_list, shell=False):
    if isinstance(cmd_or_list, str):
        print(cmd_or_list)
    else:
        print(' '.join(cmd_or_list))
    return_code = subprocess.call(cmd_or_list, shell=shell)
    return return_code


def s3cmdCanList(cfg, uri):
    cmd = ["s3cmd", "-c", cfg, "ls", uri]
    print ' '.join(cmd)
    out = subprocess.Popen(cmd,
                           stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE).communicate()[1]
    if re.search("Access.*was denied", out):
        return None
    return True

outfile = "./tmp-out"
logfile = "./tmp-log"
infile = "./tmp-in"


def s3cmdCanGet(cfg, uri):
    cmd = ["s3cmd", "-c", cfg, "get", uri, outfile, "--force"]
    return_code = subprocess.call(cmd, stderr=subprocess.STDOUT)
    return return_code == 0


def s3cmdGetDelPut(cfg, uri):
    if not s3cmdCanGet(cfg, uri):
        return None
    cmd = ["s3cmd", "-c", cfg, "del", uri]
    return_code = subprocess.call(cmd, stderr=subprocess.STDOUT)
    if return_code != 0:
        return None
    cmd = ["s3cmd", "-c", cfg, "put", outfile, uri]
    return_code = subprocess.call(cmd, stderr=subprocess.STDOUT)
    return return_code == 0


def s3cmdClearBucket(cfg, uri):
    cmd = "s3cmd -c %s ls -r %s | " \
        "awk '{print \" s3cmd -c %s del \" $NF}' | sh -v"
    cmd = cmd % (cfg, uri, cfg)
    print cmd
    return_code = subprocess.call([cmd], stderr=subprocess.STDOUT, shell=True)
    return return_code == 0


def s3cmdPutContent(cfg, uri, content):
    cmd = ["echo " + content + " > " + outfile]
    return_code = subprocess.call(cmd, shell=True)
    if return_code != 0:
        return None
    cmd = ["s3cmd", "-c", cfg, "put", outfile, uri]
    return_code = subprocess.call(cmd, stderr=subprocess.STDOUT)
    return return_code == 0


def validateCopy(cfg, uri1, uri2):
    cmd = "s3cmd -c %s ls -r --list-md5 %s | " \
        "awk '{print $4,substr($5,%d)}' > %s"
    cmd = cmd % (cfg, uri1, len(uri1)+1, outfile)
    print(cmd)
    return_code = subprocess.call([cmd], shell=True)
    if return_code != 0:
        return False
    cmd = "s3cmd -c %s ls -r --list-md5 %s | " \
        "awk '{print $4,substr($5,%d)}' | diff - %s"
    cmd = cmd % (cfg, uri2, len(uri2)+1, outfile)
    print(cmd)
    return_code = subprocess.call([cmd], shell=True)
    return return_code == 0


def validateFilesCopied(cfg, uri1, uri2, filelist):
    cmd = "rm " + outfile
    return_code = subprocess.call([cmd], shell=True)
    if return_code != 0:
        return False
    for fname in filelist:
        cmd = "s3cmd -c %s ls -r --list-md5 %s/%s | " \
            "awk '{print $4,substr($5,%d)}' >> %s"
        cmd = cmd % (cfg, uri1, fname, len(uri1)+1, outfile)
        print(cmd)
        return_code = subprocess.call([cmd], shell=True)
        if return_code != 0:
            return False
    cmd = "s3cmd -c %s ls -r --list-md5 %s | " \
        "awk '{print $4,substr($5,%d)}' | diff - %s"
    cmd = cmd % (cfg, uri2, len(uri2)+1, outfile)
    print(cmd)
    return_code = subprocess.call([cmd], shell=True)
    return return_code == 0


def s3cmdCountKeys(cfg, uri):
    cmd = "s3cmd -c %s ls -r %s | wc -l" % (cfg, uri)
    print(cmd)
    count = int(subprocess.Popen(cmd,
                                 stdout=subprocess.PIPE,
                                 shell=True).communicate()[0].strip())
    return count

folder1 = "/folder-001"
folder2 = "/folder-002"
folder3 = "/folder-003"
folder4 = "/folder-004"

file1 = "test-001"
file3 = "test-003"
file5 = "test-005"
file7 = "test-007"
file9 = "test-009"

s3copy = "./s3copy"


class S3TestCase(unittest.TestCase):

    def setUp(self):
        cmd = "s3cmd -c %s sync ./testdata/sample1/* %s" % (CFG0, TESTSRC1)
        print("setup: " + cmd)
        return_code = subprocess.call([cmd], shell=True)


class TestS3CopyBasic(S3TestCase):

    def test_simple(self):
        # clear out the destination bucket
        self.assertTrue(s3cmdClearBucket(CFG2, TESTDST1))
        # run s3copy
        cmd = [s3copy, "-c", CFG0, TESTSRC1, TESTDST1, "-l", "DEBUG",
               "-L", logfile]
        return_code = runcmd(cmd)
        self.assertTrue(return_code == 0)
        self.assertTrue(validateCopy(CFG0, TESTSRC1, TESTDST1))

    def test_file_option(self):
        srcfolder = TESTSRC1
        dstfolder = TESTDST1
        srcfiles = ['folder-001/test-001', 'folder-002/test-003']
        # clear out the destination
        self.assertTrue(s3cmdClearBucket(CFG2, dstfolder))
        # run s3copy
        command = [s3copy, "-c", CFG0, srcfolder, dstfolder, '-f']
        command.extend(srcfiles)
        return_code = runcmd(command)
        self.assertTrue(return_code == 0)
        self.assertTrue(validateFilesCopied(CFG0, srcfolder,
                                            dstfolder, srcfiles))

    def test_prefix_option(self):
        srcfolder = TESTSRC1
        dstfolder = TESTDST1
        prefixes = ['folder-001', 'folder-002']
        # clear out the destination
        self.assertTrue(s3cmdClearBucket(CFG2, dstfolder))
        # run s3copy
        command = [s3copy, "-c", CFG0, srcfolder, dstfolder, '-p']
        command.extend(prefixes)
        return_code = runcmd(command)
        self.assertTrue(return_code == 0)
        self.assertTrue(validateFilesCopied(CFG0, srcfolder,
                                            dstfolder, prefixes))

    def test_filelist_option(self):
        srcfolder = TESTSRC1
        dstfolder = TESTDST1
        srcfiles = ['folder-001/test-001', 'folder-002/test-003']
        # clear out the destination
        self.assertTrue(s3cmdClearBucket(CFG2, dstfolder))
        # setup input file
        f = open(infile, 'w')
        for filename in srcfiles:
            f.write(filename + "\n")
        f.close()
        # run s3copy
        command = [s3copy, "-c", CFG0, srcfolder, dstfolder, '-F', infile]
        return_code = runcmd(command)
        self.assertTrue(return_code == 0)
        self.assertTrue(validateFilesCopied(CFG0, srcfolder,
                                            dstfolder, srcfiles))

    def test_prefixlist_option(self):
        srcfolder = TESTSRC1
        dstfolder = TESTDST1
        prefixes = ['folder-001', 'folder-002']
        # clear out the destination
        self.assertTrue(s3cmdClearBucket(CFG2, dstfolder))
        # setup input file
        f = open(infile, 'w')
        for p in prefixes:
            f.write(p + "\n")
        f.close()
        # run s3copy
        command = [s3copy, "-c", CFG0, srcfolder, dstfolder, '-P', infile]
        return_code = runcmd(command)
        self.assertTrue(return_code == 0)
        self.assertTrue(validateFilesCopied(CFG0, srcfolder,
                                            dstfolder, prefixes))


class TestS3CopyPaths(S3TestCase):

    def test_dest_folder(self):
        dstfolder = TESTDST1 + "/test"
        # clear out the destination
        self.assertTrue(s3cmdClearBucket(CFG2, dstfolder))
        # run s3copy
        cmd = [s3copy, "-c", CFG0, TESTSRC1, dstfolder, "-l", "DEBUG",
               "-L", logfile]
        return_code = runcmd(cmd)
        self.assertTrue(return_code == 0)
        self.assertTrue(validateCopy(CFG0, TESTSRC1, dstfolder))

    def test_dest_folder_trailing_slash(self):
        dstfolder = TESTDST1 + "/test"
        # clear out the destination
        self.assertTrue(s3cmdClearBucket(CFG2, dstfolder))
        # even though there's a trailing slash, it behaves the same was as
        # though there wasn't
        cmd = [s3copy, "-c", CFG0, TESTSRC1, dstfolder + "/", "-l", "DEBUG",
               "-L", logfile]
        return_code = runcmd(cmd)
        self.assertTrue(return_code == 0)
        self.assertTrue(validateCopy(CFG0, TESTSRC1, dstfolder))

    def test_src_folder(self):
        srcfolder = TESTSRC1 + "/folder-001"
        dstfolder = TESTDST1 + "/test"
        # clear out the destination
        self.assertTrue(s3cmdClearBucket(CFG2, dstfolder))
        # run s3copy
        cmd = [s3copy, "-c", CFG0, srcfolder, dstfolder, "-l", "DEBUG",
               "-L", logfile]
        return_code = runcmd(cmd)
        self.assertTrue(return_code == 0)
        self.assertTrue(validateCopy(CFG0, srcfolder,
                                     dstfolder + "/folder-001"))

    def test_src_glob(self):
        srcfolder = TESTSRC1 + "/folder-001"
        dstfolder = TESTDST1 + "/test"
        # clear out the destination
        self.assertTrue(s3cmdClearBucket(CFG2, dstfolder))
        # run s3copy
        cmd = [s3copy, "-c", CFG0, srcfolder+"/*", dstfolder, "-l", "DEBUG",
               "-L", logfile]
        return_code = runcmd(cmd)
        self.assertTrue(return_code == 0)
        self.assertTrue(validateCopy(CFG0, srcfolder, dstfolder))


class TestS3Access(S3TestCase):

    # the tests in this class require careful setup:
    # two buckets with access policies
    # and two identities with specific as described below.

    # the following "test" does not exercise s3copy at all.
    # it uses s3cmd to validate that the buckets and accounts
    # specified in s3copy_test_settings have the desired policies set such
    # that the following s3copy tests are interesting
    def test_credentials_setup(self):
        # first, clear out the destination bucket
        self.assertTrue(s3cmdClearBucket(CFG2, TESTDST1))
        # then write a single file to it
        self.assertTrue(s3cmdPutContent(CFG2, TESTDST1 + "/" + file9,
                                        "test-009"))
        # A. the first credentials can not list the whole src bucket.
        self.assertFalse(s3cmdCanList(CFG1, TESTSRC1))
        self.assertFalse(s3cmdCanList(CFG1, TESTSRC1 + "/"))
        # B. the first credentials can list the contents of folder-001 and
        # folder-002, and can retrieve objects from these folders.
        self.assertFalse(s3cmdCanList(CFG1, TESTSRC1 + folder1))
        self.assertTrue(s3cmdCanList(CFG1, TESTSRC1 + folder1 + "/"))
        self.assertFalse(s3cmdCanList(CFG1, TESTSRC1 + folder2))
        self.assertTrue(s3cmdCanList(CFG1, TESTSRC1 + folder2 + "/"))
        self.assertTrue(s3cmdCanGet(CFG1, TESTSRC1 + folder1 + "/" + file1))
        self.assertTrue(s3cmdCanGet(CFG1, TESTSRC1 + folder2 + "/" + file3))
        # C. the first credentials can not list contents of folder-003, but may
        # retrieve objects from this folder.
        self.assertFalse(s3cmdCanList(CFG1, TESTSRC1 + folder3))
        self.assertFalse(s3cmdCanList(CFG1, TESTSRC1 + folder3 + "/"))
        self.assertTrue(s3cmdCanGet(CFG1, TESTSRC1 + folder3 + "/" + file5))
        # D. the first credentials can not list contents of folder-004, nor
        # retrieve objects from this folder.
        self.assertFalse(s3cmdCanList(CFG1, TESTSRC1 + folder4))
        self.assertFalse(s3cmdCanList(CFG1, TESTSRC1 + folder4 + "/"))
        self.assertFalse(s3cmdCanGet(CFG1, TESTSRC1 + folder4 + "/" + file7))
        # E. the first credentials can not list contents of the destination
        # bucket, but have unrestricted access to the objects in the bucket:
        self.assertFalse(s3cmdCanList(CFG1, TESTDST1))
        self.assertFalse(s3cmdCanList(CFG1, TESTDST1 + "/"))
        self.assertFalse(s3cmdCanList(CFG1, TESTDST1 + "/" + file9))
        self.assertTrue(s3cmdGetDelPut(CFG1, TESTDST1 + "/" + file9))
        # F. the second credentials has full access to the dst bucket, but no
        # access to the src bucket
        self.assertTrue(s3cmdCanList(CFG2, TESTDST1))
        self.assertTrue(s3cmdGetDelPut(CFG2, TESTDST1 + "/" + file9))
        self.assertFalse(s3cmdCanList(CFG2, TESTSRC1 + folder1))
        self.assertFalse(s3cmdCanList(CFG2, TESTSRC1 + folder1 + "/"))
        self.assertFalse(s3cmdCanList(CFG2, TESTSRC1 + folder2))
        self.assertFalse(s3cmdCanList(CFG2, TESTSRC1 + folder2 + "/"))
        self.assertFalse(s3cmdCanGet(CFG2, TESTSRC1 + folder1 + "/" + file1))
        self.assertFalse(s3cmdCanGet(CFG2, TESTSRC1 + folder2 + "/" + file3))

    def test_list_bucket_not_allowed(self):
        # clear out the destination bucket
        self.assertTrue(s3cmdClearBucket(CFG2, TESTDST1))
        # run s3copy
        return_code = runcmd([s3copy, TESTSRC1, TESTDST1, "-c", CFG1])
        self.assertTrue(return_code != 0)
        self.assertEqual(0, s3cmdCountKeys(CFG2, TESTDST1))

    def test_subfolder_list_allowed(self):
        srcfolder = TESTSRC1
        dstfolder = TESTDST1
        prefixes = ['folder-001', 'folder-002']
        # clear out the destination
        self.assertTrue(s3cmdClearBucket(CFG2, dstfolder))
        # setup input file
        f = open(infile, 'w')
        for p in prefixes:
            f.write(p + "\n")
        f.close()
        # run s3copy
        command = [s3copy, srcfolder, dstfolder,
                   '-P', infile, "-c", CFG1, "-d", CFG2]
        return_code = runcmd(command)
        self.assertTrue(return_code == 0)
        self.assertTrue(validateFilesCopied(CFG0, srcfolder,
                                            dstfolder, prefixes))

    def test_files_when_list_not_permitted(self):
        # note - support for this is limited - the source file can not be
        # bigger than 5GB
        srcfolder = TESTSRC1
        dstfolder = TESTDST1
        srcfiles = ['folder-003/test-005', 'folder-003/test-006']
        # clear out the destination
        self.assertTrue(s3cmdClearBucket(CFG2, dstfolder))
        # run s3copy
        command = [s3copy, srcfolder, dstfolder, "-c", CFG1, "-d", CFG2, "-f"]
        command.extend(srcfiles)
        return_code = runcmd(command)
        self.assertTrue(return_code == 0)
        self.assertTrue(validateFilesCopied(CFG0, srcfolder,
                                            dstfolder, srcfiles))

    def test_files_with_no_access_at_all(self):
        # note - support for this is limited - the source file can not be
        # bigger than 5GB
        srcfolder = TESTSRC1
        dstfolder = TESTDST1
        srcfiles = ['folder-004/test-007', 'folder-004/test-008']
        # clear out the destination
        self.assertTrue(s3cmdClearBucket(CFG2, dstfolder))
        # run s3copy
        command = [s3copy, srcfolder, dstfolder, "-c", CFG1, "-f"]
        command.extend(srcfiles)
        return_code = runcmd(command)
        self.assertTrue(return_code != 0)
        self.assertEqual(0, s3cmdCountKeys(CFG2, TESTDST1))


def suite():
    suites = [unittest.TestLoader().loadTestsFromTestCase(TestS3CopyBasic),
              unittest.TestLoader().loadTestsFromTestCase(TestS3CopyPaths),
              # comment out the following line if you don't want to set up
              # the complicated access rules required
              unittest.TestLoader().loadTestsFromTestCase(TestS3Access),
              ]
    suite = unittest.TestSuite(suites)
    return suite

unittest.TextTestRunner().run(suite())
