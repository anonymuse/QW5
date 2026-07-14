const std = @import("std");

pub fn build(b: *std.Build) void {
    const target = b.standardTargetOptions(.{});
    const optimize = b.standardOptimizeOption(.{});

    const qw5 = b.addModule("qw5", .{
        .root_source_file = b.path("src/root.zig"),
        .target = target,
        .optimize = optimize,
    });

    const exe = b.addExecutable(.{
        .name = "qw5",
        .root_module = b.createModule(.{
            .root_source_file = b.path("src/main.zig"),
            .target = target,
            .optimize = optimize,
            .imports = &.{.{ .name = "qw5", .module = qw5 }},
        }),
    });
    b.installArtifact(exe);

    const run = b.addRunArtifact(exe);
    run.step.dependOn(b.getInstallStep());
    if (b.args) |args| run.addArgs(args);
    const run_step = b.step("run", "Run the QW5 bootstrap command");
    run_step.dependOn(&run.step);

    const tests = b.addTest(.{ .root_module = qw5 });
    const run_tests = b.addRunArtifact(tests);
    const test_step = b.step("test", "Run unit tests");
    test_step.dependOn(&run_tests.step);

    const smoke = b.addRunArtifact(exe);
    smoke.addArg("smoke");
    smoke.expectStdOutEqual("QW5 bootstrap smoke: ok\n");
    smoke.expectStdErrEqual("");
    const smoke_step = b.step("smoke", "Run the deterministic bootstrap smoke test");
    smoke_step.dependOn(&smoke.step);
}
