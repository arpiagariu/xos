from basetest import BaseToscaTest

from core.models import Slice, Site, User, SlicePrivilege

class SliceTest(BaseToscaTest):
    tests = ["create_slice_minimal",
             "create_slice_maximal",
             "create_slice_privilege",
             "destroy_slice"]

    def cleanup(self):
        self.try_to_delete(Slice, name="testsite_testslice")
        self.try_to_delete(Site, name="testsite")

    def get_base_templates(self):
        return self.make_nodetemplate("testsite", "tosca.nodes.Site")

    def create_slice_minimal(self):
        self.assert_noobj(Slice, "testsite_testslice")
        self.execute(self.get_base_templates() +
                     self.make_nodetemplate("testsite_testslice", "tosca.nodes.Slice",
                                            reqs=[("testsite", "tosca.relationships.MemberOfSite")]))
        self.assert_obj(Slice, "testsite_testslice", enabled=True, description="", slice_url="", max_instances=10)

    def create_slice_maximal(self):
        self.assert_noobj(Slice, "testsite_testslice")
        self.execute(self.get_base_templates() +
                     self.make_nodetemplate("testsite_testslice", "tosca.nodes.Slice",
                                             props={"enabled": False, "description": "foo", "slice_url": "http://foo.com/", "max_instances": 11},
                                             reqs=[("testsite", "tosca.relationships.MemberOfSite")]))
        self.assert_obj(Slice, "testsite_testslice", enabled=False, description="foo", slice_url="http://foo.com/", max_instances=11)

    def create_slice_privilege(self):
        self.assert_noobj(Slice, "testsite_testslice")
        self.execute(self.get_base_templates() +
                     self.make_user_template() +
                     self.make_nodetemplate("testsite_testslice", "tosca.nodes.Slice",
                                            reqs=[("testsite", "tosca.relationships.MemberOfSite"),
                                                  ("test@user.com", "tosca.relationships.AdminPrivilege")]))
        slice = self.assert_obj(Slice, "testsite_testslice")
        user = User.objects.get(email="test@user.com")

        dps = SlicePrivilege.objects.filter(user=user, slice=slice)
        assert(len(dps) == 1)

    def destroy_slice(self):
        self.assert_noobj(Slice, "testsite_testslice")
        self.execute(self.get_base_templates() +
                     self.make_nodetemplate("testsite_testslice", "tosca.nodes.Slice",
                                            reqs=[("testsite", "tosca.relationships.MemberOfSite")]))
        self.assert_obj(Slice, "testsite_testslice", enabled=True, description="", slice_url="", max_instances=10)
        self.destroy(self.get_base_templates() +
                     self.make_nodetemplate("testsite_testslice", "tosca.nodes.Slice",
                                            reqs=[("testsite", "tosca.relationships.MemberOfSite")]))
        self.assert_noobj(Slice, "testsite_testslice")

if __name__ == "__main__":
    SliceTest()

