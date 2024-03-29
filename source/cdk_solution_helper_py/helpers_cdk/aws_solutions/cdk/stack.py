# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import re

import jsii
from aws_cdk import Stack, Aspects, IAspect, NestedStack
from constructs import Construct, IConstruct

from aws_solutions.cdk.aws_lambda.cfn_custom_resources.solutions_metrics import Metrics
from aws_solutions.cdk.interfaces import TemplateOptions
from aws_solutions.cdk.mappings import Mappings

RE_SOLUTION_ID = re.compile(r"^SO\d+$")
RE_TEMPLATE_FILENAME = re.compile(r"^[a-z]+(?:-[a-z]+)*\.template$")  # NOSONAR


def validate_re(name, value, regex: re.Pattern):
    if regex.match(value):
        return value
    raise ValueError(f"{name} must match '{regex.pattern}")


def validate_solution_id(solution_id: str) -> str:
    return validate_re("solution_id", solution_id, RE_SOLUTION_ID)


def validate_template_filename(template_filename: str) -> str:
    return validate_re("template_filename", template_filename, RE_TEMPLATE_FILENAME)


@jsii.implements(IAspect)
class MetricsAspect:
    def __init__(self, stack: SolutionStack):
        self.stack = stack

    def visit(self, node: IConstruct):
        """Called before synthesis, this allows us to set metrics at the end of synthesis"""
        if node == self.stack:
            self.stack.metrics = Metrics(self.stack, "Metrics", self.stack.metrics)


class SolutionStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        description: str,
        template_filename,
        **kwargs,
    ):
        super().__init__(scope, construct_id, **kwargs)

        self.metrics = {}
        self.solution_id = self.node.try_get_context("SOLUTION_ID")
        self.solution_version = self.node.try_get_context("SOLUTION_VERSION")
        self.mappings = Mappings(self, solution_id=self.solution_id)
        self.solutions_template_filename = validate_template_filename(template_filename)
        self.description = description.strip(".")
        self.solutions_template_options = TemplateOptions(
            self,
            construct_id=construct_id,
            description=f"({self.solution_id}) - {self.description}. Version {self.solution_version}",
            filename=template_filename,
        )
        Aspects.of(self).add(MetricsAspect(self))


class NestedSolutionStack(SolutionStack, NestedStack):
    """A nested version of SolutionStack"""

    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)