import axios from "axios";
import nodemailer from "nodemailer";
import querystring from "querystring";
import validator from "validator";
import { SSMClient, GetParametersCommand } from "@aws-sdk/client-ssm";

// Fetch secrets from AWS SSM
const fetchSecrets = async () => {
  const client = new SSMClient({ region: "eu-central-1" });
  const input = {
    Names: [
      "/lostindusk.com/contact/CF/SECRET_KEY",
      "/lostindusk.com/contact/ses/HOST",
      "/lostindusk.com/contact/ses/PASSWORD",
      "/lostindusk.com/contact/ses/TARGET",
      "/lostindusk.com/contact/ses/USERNAME",
    ],
    WithDecryption: true,
  };
  const command = new GetParametersCommand(input);
  const { Parameters } = await client.send(command);

  const params = {};
  Parameters.forEach((el) => {
    const key = el.Name.split("/").pop();
    params[key] = el.Value;
  });
  return params;
};

// CF Turnstile validation
const validateCFTurnstile = async (token, secretKey) => {
  try {
    const { data } = await axios.post(
      "https://challenges.cloudflare.com/turnstile/v0/siteverify",
      querystring.stringify({
        secret: secretKey,
        response: token,
      }),
      {
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
        },
      },
    );

    if (!data.success) {
      console.warn("CF Turnstile validation failed:", data["error-codes"]);
    }
    return data.success;
  } catch (err) {
    console.error("CF Turnstile validation error", err);
    return null;
  }
};

// Email sending
const sendEmail = async (params, name, email, message) => {
  const transporter = nodemailer.createTransport({
    host: params.HOST,
    port: 465,
    secure: true,
    auth: {
      user: params.USERNAME,
      pass: params.PASSWORD,
    },
  });

  try {
    const result = await transporter.sendMail({
      from: '"LostInDusk.com" <contact@lostindusk.com>',
      to: params.TARGET,
      subject: `Message from ${name} <${email}>`,
      text: `You received a message from ${name} (${email})!\n\n${message}`,
    });
    console.log("Email sent:", result.messageId);
    return true;
  } catch (err) {
    console.error("Email sending failed:", err);
    return false;
  }
};

// Lambda handler
export const handler = async (event) => {
  const headers = {
    "Access-Control-Allow-Origin": "https://lostindusk.com",
    "Access-Control-Allow-Headers":
      "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
    "Access-Control-Allow-Methods": "OPTIONS,POST",
  };

  try {
    const { token, name, email, message } = JSON.parse(event.body);

    // Basic validation
    if (
      !token ||
      !validator.isEmail(email) ||
      !validator.isLength(name, { min: 1, max: 100 }) ||
      !validator.isLength(message, { min: 1, max: 2000 })
    ) {
      return {
        statusCode: 400,
        headers,
        body: JSON.stringify({ message: "Invalid input." }),
      };
    }

    const params = await fetchSecrets();

    const isHuman = await validateCFTurnstile(token, params.SECRET_KEY);
    if (isHuman === null) {
      return {
        statusCode: 500,
        headers,
        body: JSON.stringify({ message: "Internal server error." }),
      };
    }

    if (!isHuman) {
      return {
        statusCode: 403,
        headers,
        body: JSON.stringify({ message: "Failed CF Turnstile verification." }),
      };
    }

    const emailSent = await sendEmail(params, name, email, message);
    if (!emailSent) {
      return {
        statusCode: 502,
        headers,
        body: JSON.stringify({ message: "Failed to send email." }),
      };
    }

    return {
      statusCode: 200,
      headers,
      body: JSON.stringify({ message: "Success!" }),
    };
  } catch (err) {
    console.error("Unhandled exception:", err);
    return {
      statusCode: 500,
      headers,
      body: JSON.stringify({ message: "Server error." }),
    };
  }
};
