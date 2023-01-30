#!/usr/bin/env python3

# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import jsii

import aws_cdk as cdk
from aws_cdk import aws_applicationinsights as applicationinsights
from aws_cdk import aws_servicecatalogappregistry_alpha as appreg

from constructs import Construct, IConstruct


@jsii.implements(cdk.IAspect)
class AppRegistry(Construct):
    """This construct creates the resources required for AppRegistry and injects them as Aspects"""

    def __init__(self, scope: Construct, id: str):
        super().__init__(scope, id)
        self.solution_name = scope.node.try_get_context("SOLUTION_NAME")
        self.app_registry_name = scope.node.try_get_context("APP_REGISTRY_NAME")
        self.solution_id = scope.node.try_get_context("SOLUTION_ID")
        self.solution_version = scope.node.try_get_context("SOLUTION_VERSION")
        self.application_type = scope.node.try_get_context("APPLICATION_TYPE")
        self.application: appreg.Application = None

    def visit(self, node: IConstruct) -> None:
        """The visitor method invoked during cdk synthesis"""
        if isinstance(node, cdk.Stack):
            if not node.nested:
                # parent stack
                stack: cdk.Stack = node
                self.__create_app_for_app_registry()
                self.application.associate_stack(stack)
                self.__create_attribute_group()
                self.__add_tags_for_application()
                self.__create_app_for_app_insights()
            else:
                # nested stack
                if not self.application:
                    self.__create_app_for_app_registry()

                self.application.associate_stack(node)

    def __create_app_for_app_registry(self) -> None:
        """Method to create an AppRegistry Application"""
        self.application = appreg.Application(
            self,
            "RegistrySetup",
            application_name=cdk.Fn.join("-", [cdk.Aws.STACK_NAME, self.app_registry_name]),
            description=f"Service Catalog application to track and manage all your resources for the solution {self.solution_name}",
        )

    def __add_tags_for_application(self) -> None:
        """Method to add tags to the AppRegistry's Application instance"""
        if not self.application:
            self.__create_app_for_app_registry()

        cdk.Tags.of(self.application).add("Solutions:SolutionID", self.solution_id)
        cdk.Tags.of(self.application).add("Solutions:SolutionName", self.solution_name)
        cdk.Tags.of(self.application).add("Solutions:SolutionVersion", self.solution_version)
        cdk.Tags.of(self.application).add("Solutions:ApplicationType", self.application_type)

    def __create_attribute_group(self) -> None:
        """Method to add attributes to be as associated with the Application's instance in AppRegistry"""
        if not self.application:
            self.__create_app_for_app_registry()

        self.application.associate_attribute_group(
            appreg.AttributeGroup(
                self,
                "AppAttributes",
                attribute_group_name=cdk.Aws.STACK_NAME,
                description="Attributes for Solutions Metadata",
                attributes={
                    "applicationType": self.application_type,
                    "version": self.solution_version,
                    "solutionID": self.solution_id,
                    "solutionName": self.solution_name,
                },
            )
        )

    def __create_app_for_app_insights(self) -> None:
        """Method to create resources to enable application insights"""
        if not self.application:
            self.__create_app_for_app_registry()

        dependent_resource: cdk.CfnResource = self.application.node.default_child

        applicationinsights.CfnApplication(
            self,
            "AppInsights",
            resource_group_name=cdk.Fn.join(
                "-",
                [
                    "AWS_AppRegistry_Application",
                    cdk.Aws.STACK_NAME,
                    self.app_registry_name,
                ],
            ),
            auto_configuration_enabled=True,
            cwe_monitor_enabled=True,
            ops_center_enabled=True,
        ).add_depends_on(dependent_resource)
