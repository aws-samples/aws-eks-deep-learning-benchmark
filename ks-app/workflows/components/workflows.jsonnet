local env = std.extVar("__ksonnet/environments");
local params = std.extVar("__ksonnet/params").components.workflows;
local k = import "k.libsonnet";

local workflows = import "workflows.libsonnet";
local base = workflows.new(env, params);

std.prune(k.core.v1.list.new([
    base.benchmark,
]))