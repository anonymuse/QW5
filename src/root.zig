const std = @import("std");
const builtin = @import("builtin");
const Io = std.Io;

pub const smoke_output = "QW5 bootstrap smoke: ok\n";

pub fn writeSmoke(writer: *Io.Writer) Io.Writer.Error!void {
    try writer.writeAll(smoke_output);
}

/// Writes public-safe compiler-target metadata in deterministic key order.
/// This is intentionally not a complete physical hardware inventory.
pub fn writeInventory(writer: *Io.Writer) Io.Writer.Error!void {
    try writer.print(
        "{{\"schema\":\"bootstrap-target-v1\",\"source\":\"compiler-target\",\"os\":\"{s}\",\"arch\":\"{s}\",\"pointer_bits\":{d},\"zig\":\"{s}\"}}\n",
        .{
            @tagName(builtin.os.tag),
            @tagName(builtin.cpu.arch),
            @bitSizeOf(usize),
            builtin.zig_version_string,
        },
    );
}

test "smoke output is deterministic" {
    var output: Io.Writer.Allocating = .init(std.testing.allocator);
    defer output.deinit();

    try writeSmoke(&output.writer);
    try std.testing.expectEqualStrings(smoke_output, output.written());
}

test "inventory identifies its limited schema and source" {
    var output: Io.Writer.Allocating = .init(std.testing.allocator);
    defer output.deinit();

    try writeInventory(&output.writer);
    try std.testing.expect(std.mem.indexOf(
        u8,
        output.written(),
        "\"schema\":\"bootstrap-target-v1\"",
    ) != null);
    try std.testing.expect(std.mem.indexOf(
        u8,
        output.written(),
        "\"source\":\"compiler-target\"",
    ) != null);
}
