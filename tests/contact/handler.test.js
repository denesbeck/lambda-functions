import { describe, it, expect, vi, beforeEach } from "vitest";
import { mockClient } from "aws-sdk-client-mock";
import { SSMClient, GetParametersCommand } from "@aws-sdk/client-ssm";
import { SESClient, SendEmailCommand } from "@aws-sdk/client-ses";
import axios from "axios";

vi.mock("axios");

const ssmMock = mockClient(SSMClient);
const sesMock = mockClient(SESClient);

// Valid event payload
const validEvent = {
  token: "test-turnstile-token",
  name: "John Doe",
  email: "john@example.com",
  message: "Hello, this is a test message.",
};

// SSM parameters returned by mocked SSM
const ssmParameters = [
  { Name: "/arcade-lab.io/contact/CF/SECRET_KEY", Value: "cf-secret-123" },
  { Name: "/arcade-lab.io/contact/ses/TARGET", Value: "target@example.com" },
  { Name: "/arcade-lab.io/contact/ses/SOURCE", Value: "source@example.com" },
];

let handler;

beforeEach(async () => {
  vi.resetModules();
  ssmMock.reset();
  sesMock.reset();
  vi.mocked(axios.post).mockReset();

  process.env.AWS_REGION = "us-east-1";

  // Default: SSM returns params successfully
  ssmMock.on(GetParametersCommand).resolves({ Parameters: ssmParameters });

  // Default: SES sends email successfully
  sesMock.on(SendEmailCommand).resolves({ MessageId: "mock-message-id" });

  // Default: Turnstile validates successfully
  vi.mocked(axios.post).mockResolvedValue({
    data: { success: true },
  });

  // Re-import handler after mocks are set up
  const mod = await import("../../functions/arcade-lab/contact/index.js");
  handler = mod.handler;
});

describe("contact handler", () => {
  describe("input validation", () => {
    it("returns 400 when token is missing", async () => {
      const result = await handler({ ...validEvent, token: "" });
      expect(result.statusCode).toBe(400);
      expect(JSON.parse(result.body).message).toBe("Invalid input.");
    });

    it("returns 400 when email is invalid", async () => {
      const result = await handler({ ...validEvent, email: "not-an-email" });
      expect(result.statusCode).toBe(400);
    });

    it("returns 400 when name is empty", async () => {
      const result = await handler({ ...validEvent, name: "" });
      expect(result.statusCode).toBe(400);
    });

    it("returns 400 when name exceeds 100 characters", async () => {
      const result = await handler({
        ...validEvent,
        name: "a".repeat(101),
      });
      expect(result.statusCode).toBe(400);
    });

    it("returns 400 when message is empty", async () => {
      const result = await handler({ ...validEvent, message: "" });
      expect(result.statusCode).toBe(400);
    });

    it("returns 400 when message exceeds 2000 characters", async () => {
      const result = await handler({
        ...validEvent,
        message: "a".repeat(2001),
      });
      expect(result.statusCode).toBe(400);
    });
  });

  describe("Cloudflare Turnstile validation", () => {
    it("returns 403 when Turnstile validation fails", async () => {
      vi.mocked(axios.post).mockResolvedValue({
        data: { success: false, "error-codes": ["invalid-input-response"] },
      });

      const result = await handler(validEvent);
      expect(result.statusCode).toBe(403);
      expect(JSON.parse(result.body).message).toBe(
        "Failed CF Turnstile verification.",
      );
    });

    it("returns 500 when Turnstile request throws", async () => {
      vi.mocked(axios.post).mockRejectedValue(new Error("Network error"));

      const result = await handler(validEvent);
      expect(result.statusCode).toBe(500);
      expect(JSON.parse(result.body).message).toBe("Internal server error.");
    });
  });

  describe("SES email sending", () => {
    it("returns 502 when SES fails to send email", async () => {
      sesMock.on(SendEmailCommand).rejects(new Error("SES error"));

      const result = await handler(validEvent);
      expect(result.statusCode).toBe(502);
      expect(JSON.parse(result.body).message).toBe("Failed to send email.");
    });
  });

  describe("successful flow", () => {
    it("returns 200 on successful contact submission", async () => {
      const result = await handler(validEvent);
      expect(result.statusCode).toBe(200);
      expect(JSON.parse(result.body).message).toBe("Success!");
    });

    it("calls SSM to fetch secrets", async () => {
      await handler(validEvent);
      const ssmCalls = ssmMock.commandCalls(GetParametersCommand);
      expect(ssmCalls).toHaveLength(1);
      expect(ssmCalls[0].args[0].input.Names).toEqual([
        "/arcade-lab.io/contact/CF/SECRET_KEY",
        "/arcade-lab.io/contact/ses/TARGET",
        "/arcade-lab.io/contact/ses/SOURCE",
      ]);
    });

    it("calls Turnstile with correct token and secret", async () => {
      await handler(validEvent);
      expect(vi.mocked(axios.post)).toHaveBeenCalledWith(
        "https://challenges.cloudflare.com/turnstile/v0/siteverify",
        expect.stringContaining("secret=cf-secret-123"),
        expect.objectContaining({
          headers: { "Content-Type": "application/x-www-form-urlencoded" },
        }),
      );
    });

    it("sends email via SES with correct parameters", async () => {
      await handler(validEvent);
      const sesCalls = sesMock.commandCalls(SendEmailCommand);
      expect(sesCalls).toHaveLength(1);

      const input = sesCalls[0].args[0].input;
      expect(input.Source).toBe("source@example.com");
      expect(input.Destination.ToAddresses).toEqual(["target@example.com"]);
      expect(input.Message.Subject.Data).toContain("John Doe");
      expect(input.Message.Body.Text.Data).toContain("john@example.com");
      expect(input.Message.Body.Text.Data).toContain(
        "Hello, this is a test message.",
      );
    });
  });

  describe("unhandled errors", () => {
    it("returns 500 when SSM throws unexpectedly", async () => {
      ssmMock.on(GetParametersCommand).rejects(new Error("SSM crash"));

      const result = await handler(validEvent);
      expect(result.statusCode).toBe(500);
      expect(JSON.parse(result.body).message).toBe("Server error.");
    });
  });
});
