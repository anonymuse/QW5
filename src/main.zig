const std = @import("std");
const Io = std.Io;
const qw5 = @import("qw5");

pub fn main(init: std.process.Init) !void {
    const arena = init.arena.allocator();
    const args = try init.minimal.args.toSlice(arena);

    var stdout_buffer: [1024]u8 = undefined;
    var stdout_file_writer: Io.File.Writer = .init(.stdout(), init.io, &stdout_buffer);
    const stdout = &stdout_file_writer.interface;

    if (args.len == 1 or std.mem.eql(u8, args[1], "help") or
        std.mem.eql(u8, args[1], "--help"))
    {
        try writeUsage(stdout);
    } else if (std.mem.eql(u8, args[1], "smoke")) {
        try qw5.writeSmoke(stdout);
    } else if (std.mem.eql(u8, args[1], "inventory")) {
        try qw5.writeInventory(stdout);
    } else {
        try writeUsage(stdout);
        try stdout.flush();
        return error.InvalidCommand;
    }

    try stdout.flush();
}

fn writeUsage(writer: *Io.Writer) Io.Writer.Error!void {
    try writer.writeAll(
        \\QW5 project-foundation utility
        \\
        \\Usage: qw5 <command>
        \\
        \\Commands:
        \\  smoke      emit the deterministic bootstrap smoke result
        \\  inventory  emit limited read-only compiler-target metadata
        \\  help       show this help
        \\
    );
}
