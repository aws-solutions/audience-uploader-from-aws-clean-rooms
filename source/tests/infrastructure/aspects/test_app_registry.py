#!/usr/bin/env python3

# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import pytest
import aws_cdk as cdk
from aws_cdk.assertions import Template, Capture, Match

from aspects.app_registry import AppRegistry
from lib.uploader_stack import UploaderStack
from lib.snap_uploader_stack import SnapUploaderStack
from lib.tiktok_uploader_stack import TiktokUploaderStack

FAKE_CONTEXT = {
    "SOLUTION_ID": "SO0226",
    "SOLUTION_VERSION": "%%VERSION%%",
    "BUCKET_NAME": "FAKEBUCKETNAME",
    "SOLUTION_NAME": "%%SOLUTION_NAME%%",
    "APP_REGISTRY_NAME": "FAKEAPPREGISTRYNAME",
    "APPLICATION_TYPE": "AWS-Solutions",
}


@pytest.fixture(scope="module")
def synth_base_template():

    app = cdk.App(context=FAKE_CONTEXT)
    stack = UploaderStack(
        app,
        "uploader",
        stack_name=app.node.try_get_context("STACK_NAME"),
        description=f"Audience Uploader from AWS Clean Rooms Solution CDK stack",
        template_filename="audience-uploader-from-aws-clean-rooms.template",
    )
    cdk.Aspects.of(app).add(AppRegistry(stack, "AppRegistryAspect"))
    template = Template.from_stack(stack)
    yield template, app, stack


app_registry_capture = Capture()


def test_service_catalog_registry_application(synth_base_template):
    template, app, stack = synth_base_template
    template.resource_count_is("AWS::ServiceCatalogAppRegistry::Application", 1)
    template.has_resource_properties(
        "AWS::ServiceCatalogAppRegistry::Application",
        {
            "Name": {"Fn::Join": ["-", [{"Ref": "AWS::StackName"}, app.node.try_get_context("APP_REGISTRY_NAME")]]},
            "Description": "Service Catalog application to track and manage all your resources for the solution %%SOLUTION_NAME%%",
            "Tags": {
                "Solutions:ApplicationType": "AWS-Solutions",
                "Solutions:SolutionID": "SO0226",
                "Solutions:SolutionName": "%%SOLUTION_NAME%%",
                "Solutions:SolutionVersion": "%%VERSION%%",
            },
        },
    )


def test_resource_association_nested_stacks(synth_base_template):
    template, app, stack = synth_base_template
    template.resource_count_is("AWS::ServiceCatalogAppRegistry::ResourceAssociation", 7)
    template.has_resource_properties(
        "AWS::ServiceCatalogAppRegistry::ResourceAssociation",
        {
            "Application": {"Fn::GetAtt": [app_registry_capture, "Id"]},
            "Resource": {"Ref": "AWS::StackId"},
            "ResourceType": "CFN_STACK",
        },
    )

    template.has_resource_properties(
        "AWS::ServiceCatalogAppRegistry::ResourceAssociation",
        {
            "Application": {"Fn::GetAtt": [app_registry_capture.as_string(), "Id"]},
            "Resource": {"Ref": "GlueStack"},
            "ResourceType": "CFN_STACK",
        },
    )

    template.has_resource_properties(
        "AWS::ServiceCatalogAppRegistry::ResourceAssociation",
        {
            "Application": {"Fn::GetAtt": [app_registry_capture.as_string(), "Id"]},
            "Resource": {"Ref": "ApiStack"},
            "ResourceType": "CFN_STACK",
        },
    )

    template.has_resource_properties(
        "AWS::ServiceCatalogAppRegistry::ResourceAssociation",
        {
            "Application": {"Fn::GetAtt": [app_registry_capture.as_string(), "Id"]},
            "Resource": {"Ref": "AuthStack"},
            "ResourceType": "CFN_STACK",
        },
    )

    template.has_resource_properties(
        "AWS::ServiceCatalogAppRegistry::ResourceAssociation",
        {
            "Application": {"Fn::GetAtt": [app_registry_capture.as_string(), "Id"]},
            "Resource": {"Ref": "WebStack"},
            "ResourceType": "CFN_STACK",
        },
    )

    template.has_resource_properties(
        "AWS::ServiceCatalogAppRegistry::ResourceAssociation",
        {
            "Application": {"Fn::GetAtt": [app_registry_capture.as_string(), "Id"]},
            "Resource": {"Ref": "SnapUploaderStackNestedStackSnapUploaderStackNestedStackResourceE4667E73"},
            "ResourceType": "CFN_STACK",
        },
    )

    template.has_resource_properties(
        "AWS::ServiceCatalogAppRegistry::ResourceAssociation",
        {
            "Application": {"Fn::GetAtt": [app_registry_capture.as_string(), "Id"]},
            "Resource": {"Ref": "TiktokUploaderStackNestedStackTiktokUploaderStackNestedStackResource6A4661A0"},
            "ResourceType": "CFN_STACK",
        },
    )


def test_attr_grp_association(synth_base_template):
    attr_grp_capture = Capture()
    template, app, stack = synth_base_template
    template.resource_count_is("AWS::ServiceCatalogAppRegistry::AttributeGroupAssociation", 1)
    template.has_resource_properties(
        "AWS::ServiceCatalogAppRegistry::AttributeGroupAssociation",
        {
            "Application": {"Fn::GetAtt": [app_registry_capture.as_string(), "Id"]},
            "AttributeGroup": {"Fn::GetAtt": [attr_grp_capture, "Id"]},
        },
    )

    assert (
        template.to_json()["Resources"][attr_grp_capture.as_string()]["Type"]
        == "AWS::ServiceCatalogAppRegistry::AttributeGroup"
    )


def test_service_catalog_reg_group(synth_base_template):
    template, app, stack = synth_base_template
    template.resource_count_is("AWS::ApplicationInsights::Application", 1)
    template.has_resource_properties(
        "AWS::ApplicationInsights::Application",
        {
            "ResourceGroupName": {
                "Fn::Join": [
                    "-",
                    [
                        "AWS_AppRegistry_Application",
                        {"Ref": "AWS::StackName"},
                        app.node.try_get_context("APP_REGISTRY_NAME"),
                    ],
                ]
            },
            "AutoConfigurationEnabled": True,
            "CWEMonitorEnabled": True,
            "OpsCenterEnabled": True,
        },
    )
