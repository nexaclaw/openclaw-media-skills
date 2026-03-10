#!/usr/bin/env swift

import AppKit
import Foundation

struct Arguments {
    let bundlePath: String
    let outputDir: String
    let format: String
    let scale: Int
}

enum RenderError: Error, CustomStringConvertible {
    case message(String)

    var description: String {
        switch self {
        case .message(let text):
            return text
        }
    }
}

func parseArguments() throws -> Arguments {
    var values: [String: String] = [:]
    var index = 1
    while index < CommandLine.arguments.count {
        let key = CommandLine.arguments[index]
        guard key.hasPrefix("--") else {
            throw RenderError.message("Unexpected argument: \(key)")
        }
        let nextIndex = index + 1
        guard nextIndex < CommandLine.arguments.count else {
            throw RenderError.message("Missing value for \(key)")
        }
        values[key] = CommandLine.arguments[nextIndex]
        index += 2
    }

    guard
        let bundlePath = values["--bundle"],
        let outputDir = values["--output-dir"],
        let format = values["--format"],
        let scaleText = values["--scale"],
        let scale = Int(scaleText),
        scale > 0
    else {
        throw RenderError.message(
            "Usage: render_text_scene.swift --bundle <path> --output-dir <dir> --format <png|jpg|jpeg> --scale <int>"
        )
    }

    return Arguments(bundlePath: bundlePath, outputDir: outputDir, format: format, scale: scale)
}

func readJSON(path: String) throws -> Any {
    let url = URL(fileURLWithPath: path)
    let data = try Data(contentsOf: url)
    return try JSONSerialization.jsonObject(with: data)
}

func dictionary(_ value: Any?) -> [String: Any] {
    value as? [String: Any] ?? [:]
}

func arrayOfDictionaries(_ value: Any?) -> [[String: Any]] {
    value as? [[String: Any]] ?? []
}

func string(_ value: Any?, default fallback: String = "") -> String {
    value as? String ?? fallback
}

func double(_ value: Any?, default fallback: Double = 0) -> Double {
    if let number = value as? NSNumber {
        return number.doubleValue
    }
    if let text = value as? String, let parsed = Double(text) {
        return parsed
    }
    return fallback
}

func int(_ value: Any?, default fallback: Int = 0) -> Int {
    if let number = value as? NSNumber {
        return number.intValue
    }
    if let text = value as? String, let parsed = Int(text) {
        return parsed
    }
    return fallback
}

func color(from hex: String, alpha: Double = 1.0) -> NSColor {
    var cleaned = hex.trimmingCharacters(in: .whitespacesAndNewlines)
    if cleaned.hasPrefix("#") {
        cleaned.removeFirst()
    }

    guard cleaned.count == 6, let value = Int(cleaned, radix: 16) else {
        return NSColor.black.withAlphaComponent(alpha)
    }

    let red = CGFloat((value >> 16) & 0xFF) / 255.0
    let green = CGFloat((value >> 8) & 0xFF) / 255.0
    let blue = CGFloat(value & 0xFF) / 255.0
    return NSColor(calibratedRed: red, green: green, blue: blue, alpha: CGFloat(alpha))
}

func fontWeight(_ raw: Int) -> NSFont.Weight {
    switch raw {
    case ..<500:
        return .regular
    case 500..<600:
        return .medium
    case 600..<700:
        return .semibold
    case 700..<800:
        return .bold
    default:
        return .heavy
    }
}

func systemFont(size: CGFloat, weight: NSFont.Weight) -> NSFont {
    NSFont.systemFont(ofSize: size, weight: weight)
}

func alignment(_ raw: String) -> NSTextAlignment {
    switch raw {
    case "center":
        return .center
    case "right":
        return .right
    default:
        return .left
    }
}

func drawRect(_ element: [String: Any], scale: CGFloat) {
    let rect = NSRect(
        x: double(element["x"]) * scale,
        y: double(element["y"]) * scale,
        width: double(element["width"]) * scale,
        height: double(element["height"]) * scale
    )
    let radius = double(element["radius"]) * scale
    let fill = color(from: string(element["fill"]), alpha: double(element["opacity"], default: 1.0))
    let path = NSBezierPath(
        roundedRect: rect,
        xRadius: radius,
        yRadius: radius
    )
    fill.setFill()
    path.fill()

    let strokeColor = string(element["stroke"])
    if !strokeColor.isEmpty {
        color(from: strokeColor).setStroke()
        path.lineWidth = max(CGFloat(double(element["stroke_width"], default: 1.0)) * scale, 1)
        path.stroke()
    }
}

func drawCircle(_ element: [String: Any], scale: CGFloat) {
    let radius = double(element["radius"]) * scale
    let rect = NSRect(
        x: (double(element["cx"]) * scale) - radius,
        y: (double(element["cy"]) * scale) - radius,
        width: radius * 2,
        height: radius * 2
    )
    let fill = color(from: string(element["fill"]), alpha: double(element["opacity"], default: 1.0))
    fill.setFill()
    NSBezierPath(ovalIn: rect).fill()
}

func drawText(_ element: [String: Any], scale: CGFloat) {
    let rect = NSRect(
        x: double(element["x"]) * scale,
        y: double(element["y"]) * scale,
        width: double(element["width"]) * scale,
        height: double(element["height"]) * scale
    )
    let paragraph = NSMutableParagraphStyle()
    paragraph.alignment = alignment(string(element["align"], default: "left"))
    paragraph.lineBreakMode = .byClipping

    let font = systemFont(
        size: CGFloat(double(element["size"])) * scale,
        weight: fontWeight(int(element["weight"], default: 600))
    )
    let attributes: [NSAttributedString.Key: Any] = [
        .font: font,
        .foregroundColor: color(from: string(element["color"])),
        .paragraphStyle: paragraph,
    ]
    NSString(string: string(element["text"])).draw(
        with: rect,
        options: [.usesLineFragmentOrigin, .usesFontLeading],
        attributes: attributes
    )
}

func drawElement(_ element: [String: Any], scale: CGFloat) {
    switch string(element["type"]) {
    case "rect":
        drawRect(element, scale: scale)
    case "circle":
        drawCircle(element, scale: scale)
    case "text":
        drawText(element, scale: scale)
    default:
        break
    }
}

func exportImage(
    image: NSImage,
    format: String,
    outputURL: URL
) throws {
    guard
        let tiffData = image.tiffRepresentation,
        let bitmap = NSBitmapImageRep(data: tiffData)
    else {
        throw RenderError.message("Unable to create bitmap representation")
    }

    let normalizedFormat = format == "jpeg" ? "jpg" : format
    let fileType: NSBitmapImageRep.FileType = normalizedFormat == "png" ? .png : .jpeg
    let properties: [NSBitmapImageRep.PropertyKey: Any] =
        normalizedFormat == "png" ? [:] : [.compressionFactor: 0.92]

    guard let outputData = bitmap.representation(using: fileType, properties: properties) else {
        throw RenderError.message("Unable to encode \(normalizedFormat.uppercased()) output")
    }

    try outputData.write(to: outputURL)
}

func renderCard(
    _ card: [String: Any],
    outputDir: URL,
    format: String,
    scale: Int
) throws -> URL {
    let stem = string(card["stem"])
    let scene = dictionary(card["scene"])
    let width = int(scene["width"])
    let height = int(scene["height"])
    let elements = arrayOfDictionaries(scene["elements"])

    guard width > 0, height > 0, !stem.isEmpty else {
        throw RenderError.message("Invalid scene bundle entry")
    }

    let scaledWidth = width * scale
    let scaledHeight = height * scale
    let image = NSImage(
        size: NSSize(width: scaledWidth, height: scaledHeight),
        flipped: true
    ) { _ in
        NSColor.clear.setFill()
        NSBezierPath(rect: NSRect(x: 0, y: 0, width: scaledWidth, height: scaledHeight)).fill()
        for element in elements {
            drawElement(element, scale: CGFloat(scale))
        }
        return true
    }

    let normalizedFormat = format == "jpeg" ? "jpg" : format
    let outputURL = outputDir.appendingPathComponent("\(stem).\(normalizedFormat)")
    try exportImage(image: image, format: format, outputURL: outputURL)
    return outputURL
}

do {
    let args = try parseArguments()
    let bundle = dictionary(try readJSON(path: args.bundlePath))
    let cards = arrayOfDictionaries(bundle["cards"])
    let outputDir = URL(fileURLWithPath: args.outputDir, isDirectory: true)

    try FileManager.default.createDirectory(at: outputDir, withIntermediateDirectories: true)

    for card in cards {
        let outputURL = try autoreleasepool {
            try renderCard(card, outputDir: outputDir, format: args.format, scale: args.scale)
        }
        print(outputURL.path)
    }
} catch {
    let description = (error as? CustomStringConvertible)?.description ?? error.localizedDescription
    fputs(description + "\n", stderr)
    exit(1)
}
